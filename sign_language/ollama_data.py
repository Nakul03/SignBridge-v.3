"""
Use Ollama for sign language data: validate labels, suggest signs, and get data tips.
Requires Ollama running locally (e.g. ollama serve) and a model (e.g. ollama pull llama3.2).
"""

import json
import os

# Optional: only use ollama if the package is installed
try:
    import ollama
    _OLLAMA_AVAILABLE = True
except ImportError:
    _OLLAMA_AVAILABLE = False
    ollama = None

DEFAULT_MODEL = "llama3.2"
DATA_DIR = "sign_data"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DATA_DIR, "config.json")


def _get_signs():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f).get("signs", [])
    return []


def is_available():
    """Return True if ollama package is installed and Ollama is reachable."""
    if not _OLLAMA_AVAILABLE:
        return False
    try:
        ollama.list()
        return True
    except Exception:
        return False


def suggest_label_for_landmarks(landmark_summary: str, model: str = DEFAULT_MODEL) -> str | None:
    """
    Ask Ollama to suggest which sign (from config) best matches a text description
    of hand landmark features. Used for data validation or labeling.
    landmark_summary: short text describing the hand pose (e.g. finger angles, open/closed).
    Returns suggested sign name or None if Ollama unavailable.
    """
    if not _OLLAMA_AVAILABLE or not is_available():
        return None
    signs = _get_signs()
    if not signs:
        return None
    signs_str = ", ".join(signs)
    prompt = (
        f"You are a sign language expert. Given this hand pose description, choose the single most likely sign from this exact list: [{signs_str}]. "
        f"Reply with only the sign name, nothing else.\n\nHand pose: {landmark_summary}"
    )
    try:
        response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        raw = (response.get("message") or {}).get("content", "").strip()
        for s in signs:
            if s.lower() in raw.lower() or raw.lower() == s.lower():
                return s
        return raw if raw in signs else None
    except Exception:
        return None


def validate_dataset_tips(model: str = DEFAULT_MODEL) -> str | None:
    """
    Ask Ollama for tips to improve sign language dataset quality (lighting, samples per class, etc.).
    Returns a string of tips or None.
    """
    if not _OLLAMA_AVAILABLE or not is_available():
        return None
    signs = _get_signs()
    signs_str = ", ".join(signs) if signs else "none"
    prompt = (
        "You are a sign language recognition expert. In 3-5 short bullet points, give practical tips to improve "
        "accuracy when collecting hand landmark data for these sign classes: " + signs_str + ". "
        "Focus on: number of samples per class, lighting, hand position, and avoiding confusion between similar signs."
    )
    try:
        response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        return (response.get("message") or {}).get("content", "").strip()
    except Exception:
        return None


def suggest_more_signs(limit: int = 5, model: str = DEFAULT_MODEL) -> list[str] | None:
    """
    Ask Ollama to suggest additional sign names to add to the dataset (common ASL signs).
    Returns a list of sign names or None.
    """
    if not _OLLAMA_AVAILABLE or not is_available():
        return None
    existing = _get_signs()
    prompt = (
        f"List {limit} common American Sign Language (ASL) signs that are easy to show with one hand and are NOT in this list: {existing}. "
        "Reply with only the sign names, one per line, no numbers or bullets."
    )
    try:
        response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        raw = (response.get("message") or {}).get("content", "").strip()
        suggestions = [line.strip() for line in raw.splitlines() if line.strip()]
        return suggestions[:limit]
    except Exception:
        return None


def landmarks_to_short_summary(features) -> str:
    """
    Convert a landmark feature vector to a short text summary for Ollama.
    Used when we don't have an image (e.g. validate from saved landmarks).
    """
    import numpy as np
    if features is None or len(features) < 10:
        return "unknown"
    arr = np.asarray(features)
    # Simple stats: mean, std, min, max of x,y,z groups
    n = len(arr) // 3
    xs = arr[0:n*3:3]
    ys = arr[1:n*3:3]
    zs = arr[2:n*3:3]
    parts = [
        f"x range [{xs.min():.2f}, {xs.max():.2f}], y [{ys.min():.2f}, {ys.max():.2f}]",
        f"handedness: {'right' if arr[-1] > 0.5 else 'left'}"
    ]
    return "; ".join(parts)
