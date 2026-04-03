"""
Use Ollama to validate and improve your sign language data.
Run after collect_data.py to get label suggestions and dataset tips.

Requires: pip install ollama, and Ollama running (ollama serve, ollama pull llama3.2).
"""

import json
import os
import numpy as np
from sign_language.ollama_data import (
    is_available,
    suggest_label_for_landmarks,
    validate_dataset_tips,
    suggest_more_signs,
    landmarks_to_short_summary,
)

DATA_DIR = "sign_data"
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
LANDMARKS_PATH = os.path.join(DATA_DIR, "landmarks.npy")
LABELS_PATH = os.path.join(DATA_DIR, "labels.npy")


def main():
    if not is_available():
        print("Ollama is not available. Install with: pip install ollama")
        print("Then start Ollama (e.g. ollama serve) and pull a model (e.g. ollama pull llama3.2).")
        return

    with open(CONFIG_PATH, "r") as f:
        signs = json.load(f)["signs"]

    print("=== Sign language data with Ollama ===\n")

    # 1) Dataset tips
    print("Dataset improvement tips (from Ollama):")
    tips = validate_dataset_tips()
    if tips:
        print(tips)
    else:
        print("(Could not get tips.)")
    print()

    # 2) Optional: validate a few random samples
    if os.path.exists(LANDMARKS_PATH) and os.path.exists(LABELS_PATH):
        X = np.load(LANDMARKS_PATH)
        y = np.load(LABELS_PATH)
        n = min(5, len(X))
        indices = np.random.choice(len(X), size=n, replace=False)
        print(f"Sample label check (Ollama suggestion vs your label) for {n} random samples:")
        for i in indices:
            summary = landmarks_to_short_summary(X[i])
            suggested = suggest_label_for_landmarks(summary)
            actual = signs[int(y[i])]
            match = "✓" if suggested == actual else "?"
            print(f"  {match} Your label: {actual}  |  Ollama suggests: {suggested or '?'}")
        print()

    # 3) Suggest more signs to add
    print("Suggested signs to add (from Ollama):")
    more = suggest_more_signs(limit=5)
    if more:
        for s in more:
            print(f"  - {s}")
    else:
        print("  (Could not get suggestions.)")

    print("\nDone. Re-run collect_data.py to add more signs, then train_model.py to retrain.")


if __name__ == "__main__":
    main()
