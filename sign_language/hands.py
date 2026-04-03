"""
MediaPipe hands wrapper that works with both:
- Old API: mediapipe.solutions.hands (e.g. mediapipe 0.10.x)
- New API: mediapipe.tasks.vision.HandLandmarker (newer releases)
"""

import os
import urllib.request

# Try old API first (mediapipe 0.10.x and older PyPI)
_hands = None
_drawing_utils = None
_drawing_styles = None
_use_tasks_api = False
_landmarker = None
_landmarker_2hands = None
_model_path = None

# Default model URL for Tasks API (official MediaPipe model)
HAND_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)


def _try_old_api():
    global _hands, _drawing_utils, _drawing_styles, _use_tasks_api
    try:
        import mediapipe as mp
        _hands = mp.solutions.hands
        _drawing_utils = mp.solutions.drawing_utils
        _drawing_styles = mp.solutions.drawing_styles
        _use_tasks_api = False
        return True
    except AttributeError:
        return False


def _try_tasks_api():
    """Use mediapipe.tasks.python.vision.HandLandmarker (new API)."""
    global _landmarker, _use_tasks_api, _model_path
    try:
        from mediapipe.tasks import python as mp_tasks
        from mediapipe.tasks.python import vision

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "sign_data")
        os.makedirs(data_dir, exist_ok=True)
        _model_path = os.path.join(data_dir, "hand_landmarker.task")
        if not os.path.exists(_model_path):
            print("Downloading hand_landmarker model (one-time)...")
            urllib.request.urlretrieve(HAND_LANDMARKER_MODEL_URL, _model_path)

        base_options = mp_tasks.BaseOptions(model_asset_path=_model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=vision.RunningMode.VIDEO,
        )
        _landmarker = vision.HandLandmarker.create_from_options(options)
        _use_tasks_api = True
        return True
    except Exception as e:
        print(f"Tasks API init failed: {e}")
        return False


def init_hands():
    """Initialize hand detection. Prefer old API, fall back to Tasks API."""
    if _try_old_api():
        return "solutions"
    if _try_tasks_api():
        return "tasks"
    raise RuntimeError(
        "Could not load MediaPipe hands. Try: pip uninstall mediapipe && pip install mediapipe==0.10.9"
    )


def get_hands_detector(num_hands=1):
    """Return the detector (old API: Hands, new API: HandLandmarker). num_hands=1 or 2 for two-hand (ISL) mode."""
    global _hands, _landmarker, _landmarker_2hands, _use_tasks_api
    if _hands is not None and not _use_tasks_api:
        return _hands.Hands(
            static_image_mode=False,
            max_num_hands=min(num_hands, 2),
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )
    if _use_tasks_api:
        if num_hands <= 1:
            return _landmarker
        if _landmarker_2hands is None:
            _create_2hand_landmarker()
        return _landmarker_2hands
    raise RuntimeError("Call init_hands() first.")


def _create_2hand_landmarker():
    """Create Tasks API HandLandmarker with num_hands=2 (lazy init)."""
    global _landmarker_2hands, _model_path
    from mediapipe.tasks import python as mp_tasks
    from mediapipe.tasks.python import vision
    base_options = mp_tasks.BaseOptions(model_asset_path=_model_path)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.VIDEO,
    )
    created = vision.HandLandmarker.create_from_options(options)
    _landmarker_2hands = created


def _mp_result_to_landmark_obj(raw_landmarks):
    """Convert MediaPipe raw landmarks to object with .landmark list (same format for both APIs)."""
    class LandmarkPt:
        pass
    class LandmarksObj:
        pass
    landmark_list = []
    for pt in raw_landmarks:
        lm = LandmarkPt()
        lm.x = pt.x
        lm.y = pt.y
        lm.z = pt.z
        landmark_list.append(lm)
    obj = LandmarksObj()
    obj.landmark = landmark_list
    return obj


def process_frame(detector, rgb_image):
    """
    Process an RGB frame. Returns (hand_landmarks_list, handedness_list).
    Lists have 0, 1, or 2 elements depending on detector and how many hands are visible.
    Each hand_landmarks is an object with .landmark list (21 points with .x, .y, .z).
    """
    global _use_tasks_api
    if not _use_tasks_api:
        results = detector.process(rgb_image)
        lm_list = []
        hand_list = []
        if results.multi_hand_landmarks:
            for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
                handedness = "Right"
                if results.multi_handedness and i < len(results.multi_handedness):
                    handedness = results.multi_handedness[i].classification[0].label
                lm_list.append(hand_landmarks)
                hand_list.append(handedness)
        return lm_list, hand_list

    # Tasks API
    import numpy as np
    rgb = np.ascontiguousarray(rgb_image)
    try:
        import mediapipe as mp
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    except (AttributeError, TypeError):
        from mediapipe.framework.formats import image as mp_image_module
        mp_image = mp_image_module.Image(image_format=mp_image_module.ImageFormat.SRGB, data=rgb)
    if not hasattr(process_frame, "_ts"):
        process_frame._ts = 0
    process_frame._ts += 1
    result = detector.detect_for_video(mp_image, process_frame._ts)
    lm_list = []
    hand_list = []
    if result.hand_landmarks:
        for i, raw in enumerate(result.hand_landmarks):
            handedness = "Right"
            if result.handedness and i < len(result.handedness) and result.handedness[i]:
                handedness = result.handedness[i][0].category_name
            lm_list.append(_mp_result_to_landmark_obj(raw))
            hand_list.append(handedness)
    return lm_list, hand_list


def draw_landmarks(frame, hand_landmarks, detector=None):
    """Draw hand landmarks on frame. hand_landmarks can be one object or a list of objects (for 2 hands)."""
    global _drawing_utils, _drawing_styles, _hands, _use_tasks_api
    if hand_landmarks is None:
        return
    if not isinstance(hand_landmarks, list):
        hand_landmarks = [hand_landmarks]
    for hlm in hand_landmarks:
        if hlm is None:
            continue
        if _use_tasks_api:
            _draw_landmarks_opencv(frame, hlm)
            continue
        if _drawing_utils is not None and _hands is not None:
            _drawing_utils.draw_landmarks(
                frame,
                hlm,
                _hands.HAND_CONNECTIONS,
                _drawing_styles.get_default_hand_landmarks_style(),
                _drawing_styles.get_default_hand_connections_style(),
            )


# Hand connections for drawing (MediaPipe 21-point hand)
_HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),  # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),  # index
    (0, 9), (9, 10), (10, 11), (11, 12),  # middle
    (0, 13), (13, 14), (14, 15), (15, 16),  # ring
    (0, 17), (17, 18), (18, 19), (19, 20),  # pinky
    (5, 9), (9, 13), (13, 17),  # palm
]


def _draw_landmarks_opencv(frame, hand_landmarks):
    """Draw landmarks with OpenCV when drawing_utils is not available."""
    import cv2
    h, w = frame.shape[:2]
    pts = []
    for lm in hand_landmarks.landmark:
        x = int(lm.x * w)
        y = int(lm.y * h)
        pts.append((x, y))
    for (x, y) in pts:
        cv2.circle(frame, (x, y), 4, (0, 255, 0), -1)
    for i, j in _HAND_CONNECTIONS:
        if i < len(pts) and j < len(pts):
            cv2.line(frame, pts[i], pts[j], (0, 255, 0), 2)
