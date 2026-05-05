"""
Flask app for sign language detection web interface.
Serves the frontend and /api/predict for camera frames.
"""

import base64
import json
import os
import pickle
import threading
import numpy as np
import cv2

from flask import Flask, request, jsonify, send_from_directory

# Project root (parent of app.py)
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "sign_data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
MODEL_PATH = os.path.join(DATA_DIR, "model.pkl")
SCALER_PATH = os.path.join(DATA_DIR, "scaler.pkl")
CLASS_NAMES_PATH = os.path.join(DATA_DIR, "class_names.json")

app = Flask(__name__, static_folder="static", static_url_path="")

# Loaded at startup; lock for thread-safe predict
_model = None
_scaler = None
_class_names = None
_two_hands = False
_detector = None
_predict_lock = threading.Lock()


def load_model():
    global _model, _scaler, _class_names, _two_hands, _detector
    try:
        if not os.path.exists(MODEL_PATH) or not os.path.exists(CLASS_NAMES_PATH):
            print(f"Missing model or class names: {MODEL_PATH}, {CLASS_NAMES_PATH}")
            return False
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
        with open(CLASS_NAMES_PATH, "r", encoding="utf-8") as f:
            _class_names = json.load(f)
        if not isinstance(_class_names, list):
            _class_names = list(_class_names) if hasattr(_class_names, "__iter__") else []
        _scaler = None
        if os.path.exists(SCALER_PATH):
            with open(SCALER_PATH, "rb") as f:
                _scaler = pickle.load(f)
        _two_hands = False
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                _two_hands = json.load(f).get("two_hands", False)

        from sign_language.hands import init_hands, get_hands_detector
        init_hands()
        _detector = get_hands_detector(2 if _two_hands else 1)

        n_model_classes = len(getattr(_model, "classes_", [])) or len(_class_names)
        if n_model_classes < len(_class_names):
            print(f"Note: Model was trained on {n_model_classes} signs.")

        return True

    except Exception as e:
        print(f"Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        return False


# ✅ CORRECT GLOBAL MODEL LOADING (FIX APPLIED HERE)
print("Initializing model at startup...")
_model_loaded = load_model()
print("Model init status:", _model_loaded)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/speech-to-sign")
def speech_to_sign_page():
    return send_from_directory("static", "speech-to-sign.html")


@app.route("/data/sign-info.json")
def sign_info():
    return send_from_directory("static", "data/sign-info.json")


@app.route("/data/isl-words.json")
def isl_words():
    return send_from_directory("static", "data/isl-words.json")


@app.route("/education/<path:filename>")
def education_static(filename):
    return send_from_directory(os.path.join(app.static_folder, "education"), filename)


@app.route("/speech-to-sign/letters/<path:filename>")
def speech_to_sign_letters(filename):
    return send_from_directory(os.path.join(app.static_folder, "speech-to-sign", "letters"), filename)


@app.route("/speech-to-sign/words/<path:filename>")
def speech_to_sign_words(filename):
    return send_from_directory(os.path.join(app.static_folder, "speech-to-sign", "words"), filename)


@app.route("/api/predict", methods=["POST"])
def predict():
    global _model, _scaler, _class_names, _two_hands, _detector

    if _model is None or _detector is None:
        return jsonify({"error": "Model not loaded"}), 503

    data = request.get_json()

    if not data or "image" not in data:
        return jsonify({"error": "No image"}), 400

    try:
        raw = data["image"]
        if "," in raw:
            raw = raw.split(",", 1)[1]

        img_buf = base64.b64decode(raw)
        arr = np.frombuffer(img_buf, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Invalid image"}), 400

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    except Exception as e:
        return jsonify({"error": str(e)}), 400

    from sign_language.hands import process_frame
    from sign_language.landmarks import extract_landmark_features_from_lists

    with _predict_lock:
        lm_list, hand_list = process_frame(_detector, rgb)
        feats = extract_landmark_features_from_lists(lm_list, hand_list, two_hands=_two_hands)

    if feats is None:
        return jsonify({"sign": None, "confidence": 0.0})

    try:
        X = feats.reshape(1, -1)

        if _scaler is not None:
            X = _scaler.transform(X)

        proba = _model.predict_proba(X)[0]
        idx = int(np.argmax(proba))
        confidence = float(proba[idx])

        sign = _class_names[idx]

        return jsonify({
            "sign": str(sign),
            "confidence": confidence
        })

    except Exception as e:
        app.logger.exception("Predict failed")
        return jsonify({"error": str(e), "sign": None, "confidence": 0.0}), 500


@app.route("/api/status")
def status():
    return jsonify({
        "model_loaded": _model is not None,
        "two_hands": _two_hands,
    })


if __name__ == "__main__":
    print("Loading sign language model...")
    if load_model():
        print("Model loaded. Starting server at http://127.0.0.1:5000")
    else:
        print("WARNING: Model not found.")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)