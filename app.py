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
import mediapipe as mp

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
            print(f"Note: Model was trained on {n_model_classes} signs. "
                  "To detect more (0-9, Space, words), collect samples in collect_data.py and run train_model.py again.")
        return True
    except Exception as e:
        print(f"Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        return False

_model_loaded = load_model()
print(" Model init status:", _model_loaded)

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
    try:
        print("Request received")

        global _model, _scaler, _class_names, _two_hands, _detector

        if _model is None or _detector is None:
            return jsonify({"error": "Model not loaded"}), 503

        data = request.get_json()
        if not data or "image" not in data:
            return jsonify({"error": "No image"}), 400

        # -------- Decode image --------
        raw = data["image"]
        if "," in raw:
            raw = raw.split(",", 1)[1]

        img_buf = base64.b64decode(raw)
        arr = np.frombuffer(img_buf, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Invalid image"}), 400

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # -------- Process frame --------
        from sign_language.hands import process_frame
        from sign_language.landmarks import extract_landmark_features_from_lists

        with _predict_lock:
            lm_list, hand_list = process_frame(_detector, rgb)
            feats = extract_landmark_features_from_lists(
                lm_list, hand_list, two_hands=_two_hands
            )

        if feats is None:
            return jsonify({"sign": None, "confidence": 0.0})

        # -------- Prediction --------
        X = feats.reshape(1, -1)

        if _scaler is not None:
            X = _scaler.transform(X)

        proba = _model.predict_proba(X)[0]
        idx = int(np.argmax(proba))
        confidence = float(proba[idx])

        sign = str(_class_names[idx]).strip()

        print("Prediction success:", sign, confidence)

        return jsonify({
            "sign": sign,
            "confidence": confidence
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({
            "error": str(e),
            "sign": None,
            "confidence": 0.0
        }), 500


@app.route("/api/status")
def status():
    return jsonify({
        "model_loaded": _model is not None,
        "two_hands": _two_hands,
    })


@app.route("/api/make_sentence", methods=["POST"])
def make_sentence():
    """Use Ollama to form a short logical sentence from a list of words (letters/numbers)."""
    data = request.get_json() or {}
    words = data.get("words") or []
    lang = data.get("lang", "en")
    if not words:
        return jsonify({"sentence": "", "error": None})
    fallback = " ".join(str(w) for w in words)
    try:
        import ollama
    except ImportError:
        return jsonify({"sentence": fallback, "error": None})
    words_str = ", ".join(str(w) for w in words)
    lang_hint = " in English" if lang == "en" else " in Hindi" if lang == "hi" else " in Marathi" if lang == "mr" else ""
    prompt = (
        f"Using only these words in this order: {words_str}. "
        f"Form one short logical sentence (e.g. a phrase, acronym, or meaningful line). "
        f"Reply with only the sentence{lang_hint}, nothing else. No quotes, no explanation."
    )
    try:
        r = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}])
        sentence = (r.get("message") or {}).get("content", "").strip().strip('"\'')
        return jsonify({"sentence": sentence or fallback, "error": None})
    except Exception:
        return jsonify({"sentence": fallback, "error": None})


SIGN_LANGUAGE_SYSTEM_PROMPT = """You are a helpful sign language (ASL/ISL) education assistant. You answer questions specifically about:
- American Sign Language (ASL) and Indian Sign Language (ISL)
- How to form letters A-Z, numbers 0-9, and common signs (hello, thank you, please, etc.)
- Fingerspelling, hand shapes, and tips for clear signing
- Deaf culture and communication tips
Keep answers concise, accurate, and focused on sign language. If asked something outside sign language, gently steer back to the topic."""


@app.route("/api/chat", methods=["POST"])
def chat():
    """Ollama chat for sign-language-specific questions (education tab)."""
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []
    if not message:
        return jsonify({"reply": "", "error": "Empty message"}), 400
    try:
        import ollama
    except ImportError:
        return jsonify({"reply": "Ollama is not installed. Install with: pip install ollama. Then run 'ollama serve' and pull a model (e.g. ollama pull llama3.2).", "error": "ollama_not_available"})
    messages = [{"role": "system", "content": SIGN_LANGUAGE_SYSTEM_PROMPT}]
    for h in history[-10:]:
        messages.append({"role": "user", "content": h.get("user", "")})
        messages.append({"role": "assistant", "content": h.get("assistant", "")})
    messages.append({"role": "user", "content": message})
    try:
        r = ollama.chat(model="llama3.2", messages=messages)
        reply = (r.get("message") or {}).get("content", "").strip()
        return jsonify({"reply": reply, "error": None})
    except Exception as e:
        return jsonify({"reply": "", "error": str(e)})

mp.solutions.hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

if __name__ == "__main__":
    print("Loading sign language model...")
    if load_model():
        print("Model loaded. Starting server at http://127.0.0.1:5000")
    else:
        print("WARNING: Model not found. Run collect_data.py and train_model.py first.")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

