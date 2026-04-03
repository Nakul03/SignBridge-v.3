"""
Reset collected sign data to zero. Deletes landmarks.npy and labels.npy
so you can run collect_data.py and retrain from scratch.
"""

import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "sign_data")
LANDMARKS_PATH = os.path.join(DATA_DIR, "landmarks.npy")
LABELS_PATH = os.path.join(DATA_DIR, "labels.npy")

def main():
    removed = []
    if os.path.exists(LANDMARKS_PATH):
        os.remove(LANDMARKS_PATH)
        removed.append("landmarks.npy")
    if os.path.exists(LABELS_PATH):
        os.remove(LABELS_PATH)
        removed.append("labels.npy")
    if removed:
        print("Removed:", ", ".join(removed))
        print("Data collection count is now 0. Run collect_data.py to collect fresh data.")
    else:
        print("No collected data found (landmarks.npy / labels.npy). Already at 0.")
    print("Config and class_names in sign_data/ are kept; only landmark/label data was cleared.")

if __name__ == "__main__":
    main()
