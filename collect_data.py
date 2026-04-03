"""
Collect hand landmark data for sign language gestures (ISL/ASL, 1 or 2 hands).
Show a sign to the camera, then press the key for the corresponding class to record samples.
Data is saved under project folder sign_data/ and is NOT deleted when training or when zipping.
"""

import cv2
import json
import numpy as np
import os
import string
from sign_language.landmarks import extract_landmark_features_from_lists, get_landmark_dim
from sign_language.hands import init_hands, get_hands_detector, process_frame, draw_landmarks
try:
    from sign_language.ollama_data import is_available, validate_dataset_tips
except ImportError:
    def is_available():
        return False
    def validate_dataset_tips():
        return None

# Project-root-relative paths so data persists when project is zipped or moved
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "sign_data")

# Default signs: A-Z, 0-9, Space, and common words for mute/deaf sign language
COMMON_WORDS = [
    "Hi", "Hello", "Bye", "ThankYou", "Welcome", "Yes", "No", "Please", "Sorry", "Help",
    "Good", "Morning", "Night", "Love", "Water", "Food", "Name", "What", "Where", "When",
    "Why", "How", "You", "We", "They", "Me", "My", "Your", "Friend", "Family", "Home",
    "School", "Work", "Come", "Go", "Stop", "Wait", "Again", "Slow", "Understand",
    "DontUnderstand", "Deaf", "Hearing"
]
DEFAULT_SIGNS = list(string.ascii_uppercase) + list(string.digits) + ["Space"] + COMMON_WORDS
SAMPLES_PER_CLASS = 80  # Number of frames to record per sign

# UI: camera large on left, instructions panel on right
CAM_WIDTH = 960
CAM_HEIGHT = 720
PANEL_WIDTH = 380
PANEL_HEIGHT = 720
FONT_SCALE = 0.55
FONT_THICK = 1
LINE_H = 28


def _instruction_for_class(signs, current_class, space_class_index, first_word_index):
    """One-line instruction shown on screen for current class."""
    name = signs[current_class]
    if current_class <= 25:
        key = chr(ord("a") + current_class)
        return f"For '{name}' press '{key}'"
    if 26 <= current_class <= 35:
        return f"For '{name}' press '{current_class - 26}'"
    if current_class == space_class_index:
        return "For SPACE press SPACEBAR"
    if first_word_index >= 0 and current_class >= first_word_index:
        return f"For '{name}' press TAB to select, then 'R' to record"
    return f"For '{name}' press 'N' to select, then 'R' to record"


def main():
    api = init_hands()
    print(f"Using MediaPipe API: {api}")

    os.makedirs(DATA_DIR, exist_ok=True)
    config_path = os.path.join(DATA_DIR, "config.json")

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        signs = config["signs"]
        two_hands = config.get("two_hands", True)
        print(f"Loaded {len(signs)} signs. Mode: {'2 hands (ISL/ASL)' if two_hands else '1 hand'}")
    else:
        signs = DEFAULT_SIGNS.copy()
        two_hands = True
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"signs": signs, "two_hands": two_hands}, f, indent=2)
        print(f"Created config with signs: A-Z, 0-9, Space + {len(COMMON_WORDS)} words.")

    hands = get_hands_detector(2 if two_hands else 1)

    data_path = os.path.join(DATA_DIR, "landmarks.npy")
    labels_path = os.path.join(DATA_DIR, "labels.npy")
    expected_dim = get_landmark_dim(two_hands=two_hands)
    if os.path.exists(data_path):
        X = np.load(data_path, allow_pickle=True).tolist()
        y = np.load(labels_path, allow_pickle=True).tolist()
        if X:
            first_len = len(X[0]) if hasattr(X[0], "__len__") else 0
            if first_len != expected_dim:
                if first_len == 64 and expected_dim == 128:
                    X = [np.concatenate([np.asarray(x).flatten(), np.zeros(64, dtype=np.float32)]) for x in X]
                elif first_len == 128 and expected_dim == 64:
                    X = [np.asarray(x).flatten()[:64].astype(np.float32) for x in X]
                else:
                    X, y = [], []
                    print("Existing data has different feature size; starting fresh for this session.")
        counts = {s: int(np.sum(np.array(y) == i)) for i, s in enumerate(signs)}
    else:
        X = []
        y = []
        counts = {s: 0 for s in signs}

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    current_class = 0
    collecting = False
    collect_count = 0
    try:
        space_class_index = signs.index("Space")
    except ValueError:
        space_class_index = -1
    first_word_index = space_class_index + 1 if space_class_index >= 0 and len(signs) > space_class_index + 1 else -1
    if first_word_index < 0:
        for i, s in enumerate(signs):
            if len(s) > 1 and s != "Space":
                first_word_index = i
                break

    if is_available():
        tips = validate_dataset_tips()
        if tips:
            print("Ollama tips for better data:\n" + tips + "\n")

    print("Controls:")
    print("  A–Z: press a–z to record that LETTER")
    print("  0–9: press number key to record that DIGIT")
    if space_class_index != -1:
        print("  SPACEBAR: record for SPACE")
    if first_word_index >= 0:
        print("  TAB: cycle through WORD signs, R or ENTER: start recording for current word")
    print("  N: next class (cycle)")
    print("  S: save and exit (data is kept; never deleted by training)")
    print("  Q: quit without saving")
    if two_hands:
        print("  1 or 2 hands in frame — both work.\n")

    # Build instructions panel text (right side)
    def draw_panel(panel):
        panel[:] = (40, 44, 52)
        y_pos = 24
        title = "INSTRUCTIONS"
        cv2.putText(panel, title, (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y_pos += LINE_H + 10
        instr = _instruction_for_class(signs, current_class, space_class_index, first_word_index)
        cv2.putText(panel, "Current:", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, (200, 200, 200), FONT_THICK)
        y_pos += LINE_H
        cv2.putText(panel, instr, (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, (0, 255, 200), FONT_THICK)
        y_pos += LINE_H + 12
        cv2.putText(panel, f"Class: {signs[current_class]} ({current_class})", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, (255, 255, 255), FONT_THICK)
        y_pos += LINE_H
        cv2.putText(panel, f"Samples: {SAMPLES_PER_CLASS} per class", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, (200, 200, 200), FONT_THICK)
        y_pos += LINE_H
        cv2.putText(panel, f"Collected this class: {counts.get(signs[current_class], 0)}", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, (0, 255, 0), FONT_THICK)
        y_pos += LINE_H + 14
        if collecting:
            cv2.putText(panel, ">>> RECORDING <<<", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)
            y_pos += LINE_H + 8
        cv2.putText(panel, "Letters: a-z | Digits: 0-9", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        y_pos += LINE_H
        cv2.putText(panel, "Space: SPACEBAR | Words: TAB then R", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        y_pos += LINE_H
        cv2.putText(panel, "Next: N | Save: S | Quit: Q", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        y_pos += LINE_H + 20
        cv2.putText(panel, "Data is saved in sign_data/", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
        y_pos += LINE_H
        cv2.putText(panel, "Include that folder when zipping.", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)

    panel = np.zeros((PANEL_HEIGHT, PANEL_WIDTH, 3), dtype=np.uint8)
    full_width = CAM_WIDTH + PANEL_WIDTH
    full_height = max(CAM_HEIGHT, PANEL_HEIGHT)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        lm_list, hand_list = process_frame(hands, rgb)

        draw_landmarks(frame, lm_list, hands)

        feats = extract_landmark_features_from_lists(lm_list, hand_list, two_hands=two_hands)
        if collecting and feats is not None:
            X.append(feats)
            y.append(current_class)
            collect_count += 1
            counts[signs[current_class]] = counts.get(signs[current_class], 0) + 1
            if collect_count >= SAMPLES_PER_CLASS:
                collecting = False
                collect_count = 0
                print(f"Recorded {SAMPLES_PER_CLASS} samples for '{signs[current_class]}'.")

        # Resize camera to left side (big)
        frame_resized = cv2.resize(frame, (CAM_WIDTH, CAM_HEIGHT))
        mode_text = " [1 or 2 hands]" if two_hands else ""
        cv2.putText(frame_resized, f"{signs[current_class]}{mode_text}", (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        if collecting:
            cv2.putText(frame_resized, "RECORDING...", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        hands_visible = f"Hands: {len(lm_list)}/2" if two_hands else ""
        cv2.putText(frame_resized, hands_visible, (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        draw_panel(panel)
        combined = np.zeros((full_height, full_width, 3), dtype=np.uint8)
        combined[:CAM_HEIGHT, :CAM_WIDTH] = frame_resized
        combined[:PANEL_HEIGHT, CAM_WIDTH:CAM_WIDTH + PANEL_WIDTH] = panel
        cv2.imshow("Collect sign data — camera (left) | instructions (right)", combined)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("s"):
            if len(X) > 0:
                X_arr = np.stack([np.asarray(x).flatten() for x in X], axis=0).astype(np.float32)
                np.save(data_path, X_arr)
                np.save(labels_path, np.array(y))
                print("Data saved to", data_path, "— training will NOT delete it.")
            break
        if key == 32:
            if space_class_index != -1:
                current_class = space_class_index
                collecting = True
                collect_count = 0
                print(f"Recording class '{signs[current_class]}'...")
        elif key == 9 and first_word_index >= 0:
            # TAB: cycle through word signs (so 'W' can stay for letter W)
            current_class = first_word_index + ((current_class - first_word_index + 1) % (len(signs) - first_word_index))
            print(f"Word class: '{signs[current_class]}' — press R or Enter to record.")
        elif ord("a") <= key <= ord("z") or ord("A") <= key <= ord("Z"):
            idx = (key - ord("a")) if key >= ord("a") else (key - ord("A"))
            if idx < len(signs):
                current_class = idx
                collecting = True
                collect_count = 0
                print(f"Recording class '{signs[current_class]}'...")
        elif 48 <= key <= 57:
            digit = key - 48
            if len(signs) >= 36:
                idx = 26 + digit
            else:
                idx = digit
            if idx < len(signs):
                current_class = idx
                collecting = True
                collect_count = 0
                print(f"Recording class '{signs[current_class]}'...")
        elif (key == ord("r") or key == 13) and current_class < len(signs):
            collecting = True
            collect_count = 0
            print(f"Recording class '{signs[current_class]}'...")
        elif key == ord("n"):
            current_class = (current_class + 1) % len(signs)
            collecting = False
            collect_count = 0
            print(f"Selected class '{signs[current_class]}' — press the key for this sign to record.")

    cap.release()
    cv2.destroyAllWindows()
    if hasattr(hands, "close"):
        hands.close()


if __name__ == "__main__":
    main()
