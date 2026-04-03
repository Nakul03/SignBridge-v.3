# Vāgbodha — Where Silence Finds Its Voice

Real-time sign language detection and **Speech to Indian Sign Language (ISL)** in one app. Uses **MediaPipe** for hand tracking and an **ensemble classifier** (Random Forest + Gradient Boosting) on hand landmark features. Supports **A–Z, 0–9, Space, and common words** (Hi, Hello, Thank you, etc.) in **ISL and ASL** with **one or two hands**. The website is **HTML, CSS, and JavaScript** served by Flask with four tabs:

- **Home** — intro and how it works  
- **Education** — sign reference (A–Z, 0–9, words) + Ollama sign-language chatbot  
- **Detector** — full-screen camera, live sign recognition, TTS, sentence building, braille-style vibrations  
- **Speech to Sign** — speak into the mic; your words are shown as Indian Sign Language images/GIFs (ISL dataset included)

## Data and model when zipping or moving the project

- **Collected data is never deleted** by training or by the app. `train_model.py` only **reads** `landmarks.npy` and `labels.npy` and **writes** `model.pkl`, `scaler.pkl`, and `class_names.json`. It also creates a **backup** copy in `sign_data/backup/` before training.
- **When zipping the project**, include the **`sign_data/`** folder so data and model are preserved on another PC.

---

## Setup

```bash
pip install -r requirements.txt
```

**Ollama (optional):** Install [Ollama](https://ollama.com), run `ollama serve`, and pull a model (e.g. `ollama pull llama3.2`). Used for dataset tips during collection and for the Education-tab sign-language chatbot.

---

## Workflow

### 1. Collect data

```bash
python collect_data.py
```

- **Large camera** on the left, **instructions** on the right.
- **Letters A–Z:** press **a–z**. **Digits 0–9:** press **0–9**. **Space:** press **Spacebar**.
- **Words:** press **TAB** to cycle to a word, then **R** or **Enter** to record.
- **N:** next class. **S:** save and exit. **Q:** quit without saving.

Aim for **about 80 samples per sign**. **Two-hand mode** is on by default; 1 or 2 hands in frame both work.

### 2. Train the model

```bash
python train_model.py
```

Trains on `sign_data/landmarks.npy` and `sign_data/labels.npy`; does not delete them. Writes `model.pkl`, `scaler.pkl`, and `class_names.json` into `sign_data/`.

### 3. Run the website

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

- **Home:** intro and how it works.
- **Education:** sign reference (A–Z, 0–9, words) with descriptions; add images in `static/education/` (e.g. `A.png`, `Hello.png`). **Chatbox** at the bottom: sign-language chatbot (Ollama).
- **Detector:** full-screen camera and output below. **Next word (speak & clear)**, **Speak word** / **Speak sentence**, **Braille vibration**. Space between words only when you show the Space sign.
- **Speech to Sign:** click **Start listening**, allow the microphone, and speak. Your speech is converted to text and displayed as ISL images or GIFs. Say **goodbye** or click **Stop** when done. Uses the included ISL dataset (letters + phrase GIFs).

---

## Project structure

```
Vāgbodha/
├── app.py                    # Flask app: static site + /api/predict, /api/chat, /api/make_sentence, /data, /speech-to-sign
├── collect_data.py           # Data collection: camera + instructions panel, saves to sign_data/
├── train_model.py            # Train ensemble; saves model, scaler, class_names; backs up data
├── reset_data.py             # Reset collected data to 0 (deletes landmarks.npy, labels.npy) for fresh collection
├── detect_realtime.py        # Desktop webcam detection (OpenCV window)
├── validate_with_ollama.py   # Optional: validate labels and get tips via Ollama
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
├── sign_language/            # Core ML & hand-detection package
│   ├── __init__.py
│   ├── hands.py              # MediaPipe wrapper (1 or 2 hands), process_frame, draw_landmarks
│   ├── landmarks.py          # Feature extraction: 64-dim per hand, 128 for two-hand
│   └── ollama_data.py        # Ollama: dataset tips, label suggestions, sign ideas
│
├── sign_data/                # Data & model (include when zipping)
│   ├── config.json           # List of signs (A–Z, 0–9, Space, words), two_hands flag
│   ├── landmarks.npy         # Collected landmark features (not deleted by training)
│   ├── labels.npy            # Class labels per sample (not deleted by training)
│   ├── model.pkl             # Trained ensemble (Random Forest + Gradient Boosting)
│   ├── scaler.pkl            # Feature scaler for inference
│   ├── class_names.json      # Sign names in order
│   ├── backup/               # Optional backup of .npy before training
│   └── hand_landmarker.task  # MediaPipe model (downloaded on first run if using Tasks API)
│
└── static/                   # Website (HTML, CSS, JS)
    ├── index.html            # Single-page app: Home, Education, Detector, Speech to Sign
    ├── css/
    │   └── style.css         # Styles: teal/coral theme, cards, detector, speech-to-sign
    ├── js/
    │   ├── app.js            # Camera, predict loop, sentence, TTS, Next word, braille
    │   ├── translations.js   # Sign labels & TTS language (en, hi, mr)
    │   ├── braille-vibrations.js   # Vibration patterns per sign (navigator.vibrate)
    │   ├── tabs-and-education.js   # Tab switching, sign grid, Ollama chat
    │   └── speech-to-sign.js # Speech-to-text (Web Speech API) + ISL display
    ├── data/
    │   ├── sign-info.json    # Sign descriptions for Education tab
    │   └── isl-words.json    # Phrase/word → filename map for Speech to Sign (ISL)
    ├── education/            # Optional: A.png, Hello.png, etc. for Education tab
    └── speech-to-sign/       # ISL assets (included from Automatic-Indian-Sign-Language-Translator-ISL)
        ├── letters/          # a.jpg–z.jpg for letter-by-letter signing
        └── words/            # Phrase GIFs (hello.gif, good morning.gif, etc.)
```

---

## Speech to Sign (ISL) tab

The **Speech to Sign** tab converts your speech to text and displays **Indian Sign Language (ISL)** images or GIFs. The project includes the [Automatic-Indian-Sign-Language-Translator-ISL](https://github.com/satyam9090/Automatic-Indian-Sign-Language-Translator-ISL) dataset: **letters** (a.jpg–z.jpg) and **ISL_Gifs** (hello.gif, good morning.gif, etc.) are already in `static/speech-to-sign/letters/` and `static/speech-to-sign/words/`.

**How to use:** Open the **Speech to Sign** tab, click **Start listening**, allow the microphone, and speak. Your words are shown as ISL signs in order. Say **goodbye** or click **Stop** when done. The app matches phrases first (e.g. “good morning”), then single words, then spells out letters.

The **sign detection model** (camera → sign recognition) is separate and lives in **Detector** and `sign_data/`; Speech to Sign does not use or modify it.

---

## Tips

- Use good lighting. **Two-hand mode:** 1 or 2 hands in frame both work.
- Include **sign_data/** when zipping or copying the project so data and model are preserved.
- Add or edit signs in `sign_data/config.json`, then collect for new classes and run `train_model.py` again.
- To **start data collection from scratch**, run `python reset_data.py` (removes `landmarks.npy` and `labels.npy`), then run `collect_data.py` and `train_model.py` again.

**Only A–Z detected?** The model only predicts signs it was trained on. If you only collected data for letters, it will only output A–Z. To get **0–9, Space, and words**, run `collect_data.py`, record samples for digits (press **0–9**), Space (press **Spacebar**), and words (use **TAB** then **R**), then run `train_model.py` again. On startup, the app prints a note if the model has fewer classes than the full sign list.

**Note:** If a `frontend/` folder is still present from an earlier React/Node setup, you can delete it manually (close any terminal or IDE using it first). The app uses only the `static/` HTML, CSS, and JS site.
