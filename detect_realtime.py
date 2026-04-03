"""
Real-time sign language detection using webcam.
Requires a trained model (run collect_data.py then train_model.py first).
"""

import cv2
import json
import os
import pickle
import numpy as np
from collections import deque, Counter
from sign_language.landmarks import extract_landmark_features_from_lists
from sign_language.hands import init_hands, get_hands_detector, process_frame, draw_landmarks

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "sign_data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
MODEL_PATH = os.path.join(DATA_DIR, "model.pkl")
SCALER_PATH = os.path.join(DATA_DIR, "scaler.pkl")
CLASS_NAMES_PATH = os.path.join(DATA_DIR, "class_names.json")

# Smoothing: average over last N predictions to reduce jitter
SMOOTH_LEN = 9
MIN_CONFIDENCE = 0.45  # Only show sign when confidence above this


def main():
    if not os.path.exists(MODEL_PATH) or not os.path.exists(CLASS_NAMES_PATH):
        print("Model not found. Run collect_data.py then train_model.py first.")
        return

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(CLASS_NAMES_PATH, "r") as f:
        class_names = json.load(f)
    scaler = None
    if os.path.exists(SCALER_PATH):
        with open(SCALER_PATH, "rb") as f:
            scaler = pickle.load(f)

    two_hands = False
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            two_hands = json.load(f).get("two_hands", False)
    print(f"Mode: {'2 hands (ISL)' if two_hands else '1 hand'}")

    api = init_hands()
    print(f"Using MediaPipe API: {api}")
    hands = get_hands_detector(2 if two_hands else 1)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam.")
        return

    history = deque(maxlen=SMOOTH_LEN)
    sentence = ""
    current_word = ""
    last_sign_in_history = ""

    print("Real-time sign language detection. Press 'q' to quit.")
    print(f"Classes: {class_names}\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        lm_list, hand_list = process_frame(hands, rgb)

        feats = extract_landmark_features_from_lists(lm_list, hand_list, two_hands=two_hands)
        if lm_list:
            draw_landmarks(frame, lm_list, hands)
        if feats is not None:
            X = feats.reshape(1, -1)
            if scaler is not None:
                X = scaler.transform(X)
            pred = model.predict(X)[0]
            proba = model.predict_proba(X)[0]
            confidence = float(np.max(proba))
            history.append((pred, confidence))
        else:
            history.clear()
            last_sign_in_history = "" # Reset when no hands are visible

        # Smoothed prediction
        current_sign = ""
        if len(history) >= SMOOTH_LEN // 2:
            preds = [p for p, c in history if c >= MIN_CONFIDENCE]
            if preds:
                most_common = Counter(preds).most_common(1)[0]
                current_sign = class_names[most_common[0]]

        # Sentence logic
        if current_sign != last_sign_in_history:
            if current_sign == "Space":
                if current_word:
                    sentence += current_word + " "
                    current_word = ""
            elif len(current_sign) == 1: # Assuming single characters are letters/digits
                current_word += current_sign
            elif current_sign: # A full word like "Hello", "Thanks"
                 sentence += current_sign + " "
        
        last_sign_in_history = current_sign

        # Draw result
        full_sentence = sentence + current_word
        cv2.putText(
            frame,
            f"Sentence: {full_sentence}",
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2,
        )
        if history:
            _, conf = history[-1]
            cv2.putText(
                frame,
                f"Confidence: {conf:.0%}",
                (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
        
        # Display current sign for debugging/clarity
        cv2.putText(
            frame,
            f"Sign: {current_sign}",
            (10, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2,
        )

        cv2.imshow("Vagbodha — Sign language detection", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    if hasattr(hands, "close"):
        hands.close()


if __name__ == "__main__":
    main()
