"""Extract hand landmark features for sign language classification."""

import numpy as np


def _single_hand_features(hand_landmarks, handedness: str) -> np.ndarray:
    """Convert one hand's landmarks to a 64-dim vector (normalized + handedness)."""
    points = []
    for lm in hand_landmarks.landmark:
        points.extend([lm.x, lm.y, lm.z])
    arr = np.array(points, dtype=np.float32)
    wrist = arr[:3].copy()
    for i in range(0, len(arr), 3):
        arr[i : i + 3] -= wrist
    scale = np.linalg.norm(arr[9:12] - arr[0:3])
    if scale > 1e-6:
        arr = arr / scale
    handed = 1.0 if handedness == "Right" else 0.0
    arr = np.append(arr, handed)
    return arr


def extract_landmark_features(hand_landmarks, handedness: str = "Right") -> np.ndarray | None:
    """
    Single-hand: convert one hand's landmarks to a 64-dim feature vector.
    Returns None if no hand is present.
    """
    if hand_landmarks is None:
        return None
    return _single_hand_features(hand_landmarks, handedness)


# 64-dim zero vector for "no hand" when in two-hand mode (pad missing hand)
_EMPTY_HAND = np.zeros(64, dtype=np.float32)


def extract_landmark_features_from_lists(
    hand_landmarks_list, handedness_list, two_hands: bool = False
) -> np.ndarray | None:
    """
    Extract features from process_frame() output (lists of hands).
    - two_hands=False: use first hand only, return 64-dim or None.
    - two_hands=True: accept 1 or 2 hands; always return 128-dim (Left then Right).
      If only one hand is visible, the other slot is padded with zeros.
    """
    if not hand_landmarks_list or not handedness_list:
        return None
    if not two_hands:
        return _single_hand_features(hand_landmarks_list[0], handedness_list[0])
    # Two-hand mode: 128-dim with canonical order [Left, Right]; pad missing hand with zeros
    left_feat = _EMPTY_HAND.copy()
    right_feat = _EMPTY_HAND.copy()
    for hlm, hand in zip(hand_landmarks_list, handedness_list):
        f = _single_hand_features(hlm, hand)
        if hand == "Left":
            left_feat = f
        else:
            right_feat = f
    return np.concatenate([left_feat, right_feat])


def get_landmark_dim(two_hands: bool = False):
    """Number of features: 64 for one hand, 128 for two hands."""
    return 128 if two_hands else 64
