"""
Train the sign language classifier on collected landmark data.
Data (landmarks.npy, labels.npy) is NEVER deleted — only read. Model files are written separately.
When zipping the project, include the sign_data/ folder so data and model travel together.
"""

import json
import os
import shutil
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "sign_data")
MODEL_PATH = os.path.join(DATA_DIR, "model.pkl")
SCALER_PATH = os.path.join(DATA_DIR, "scaler.pkl")
CLASS_NAMES_PATH = os.path.join(DATA_DIR, "class_names.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")

AUGMENT_FACTOR = 3
AUGMENT_NOISE_STD = 0.03


def augment_features(X: np.ndarray, y: np.ndarray, noise_std: float = AUGMENT_NOISE_STD, factor: int = AUGMENT_FACTOR):
    if factor <= 0:
        return X, y
    X_list, y_list = [X], [y]
    for _ in range(factor - 1):
        noise = np.random.RandomState(42).normal(0, noise_std, size=X.shape).astype(np.float32)
        noise[:, -1] = 0
        X_list.append(X + noise)
        y_list.append(y)
    return np.vstack(X_list), np.concatenate(y_list)


def main():
    data_path = os.path.join(DATA_DIR, "landmarks.npy")
    labels_path = os.path.join(DATA_DIR, "labels.npy")
    config_path = os.path.join(DATA_DIR, "config.json")

    if not os.path.exists(data_path) or not os.path.exists(labels_path):
        print("No data found. Run collect_data.py first to record sign samples.")
        return

    # Backup data before training (optional; data is never deleted by this script)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    try:
        shutil.copy2(data_path, os.path.join(BACKUP_DIR, "landmarks.npy"))
        shutil.copy2(labels_path, os.path.join(BACKUP_DIR, "labels.npy"))
    except Exception as e:
        print("Backup warning:", e)

    X = np.load(data_path, allow_pickle=True).astype(np.float32)
    y = np.load(labels_path, allow_pickle=True)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    class_names = config["signs"]

    n_classes = len(np.unique(y))
    if n_classes < 2:
        print("Need at least 2 different sign classes. Collect more data.")
        return
    if len(X) < 20:
        print("Need more samples (at least ~20). Collect more data.")
        return

    X_aug, y_aug = augment_features(X, y)
    print(f"Training on {len(X)} original + {len(X_aug) - len(X)} augmented = {len(X_aug)} samples, {n_classes} classes")
    print("(Data in sign_data/ is kept; not deleted.)")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_aug)

    rf = RandomForestClassifier(n_estimators=150, max_depth=18, min_samples_leaf=2, random_state=42)
    gb = GradientBoostingClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
    ensemble = VotingClassifier(
        estimators=[("rf", rf), ("gb", gb)],
        voting="soft",
        weights=[1, 1],
    )

    scores = cross_val_score(ensemble, X_scaled, y_aug, cv=4)
    print(f"Cross-validation accuracy: {scores.mean():.2%} (+/- {scores.std() * 2:.2%})")

    X_train, X_val, y_train, y_val = train_test_split(X_scaled, y_aug, test_size=0.2, stratify=y_aug, random_state=42)
    ensemble.fit(X_train, y_train)
    val_acc = ensemble.score(X_val, y_val)
    print(f"Validation accuracy: {val_acc:.2%}")

    ensemble.fit(X_scaled, y_aug)

    import pickle
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(ensemble, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)
    with open(CLASS_NAMES_PATH, "w", encoding="utf-8") as f:
        json.dump(class_names, f, indent=2)

    print(f"Model saved to {MODEL_PATH}")
    print(f"Scaler saved to {SCALER_PATH}")
    print(f"Class names saved to {CLASS_NAMES_PATH}")
    print("When zipping the project, include the sign_data/ folder so data and model are preserved.")


if __name__ == "__main__":
    main()
