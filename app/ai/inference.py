"""
inference.py
Loads the trained AI/NLP models (TF-IDF + Logistic Regression) and exposes
functions used by the API routes to:
  - clean/preprocess complaint text
  - classify the complaint category
  - predict priority
  - detect sentiment
  - map category -> responsible department
  - detect duplicate/similar complaints using TF-IDF cosine similarity
  - compute an overall AI confidence score
"""

import os
import re
import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(BASE_DIR, "model")

# ---------------------------------------------------------------------------
# Category -> Department mapping
# ---------------------------------------------------------------------------
CATEGORY_DEPARTMENT_MAP = {
    "IT/Network": "IT Support Department",
    "Infrastructure": "Civil & Maintenance Department",
    "Laboratory": "Laboratory & Equipment Department",
    "Library": "Library Administration",
    "Hostel": "Hostel Management",
    "Transport": "Transport Department",
    "Electricity": "Electrical Maintenance Department",
    "Cleanliness": "Housekeeping Department",
    "Examination": "Examination Cell",
    "Administration": "Administration Office",
    "Security": "Campus Security",
    "Other": "General Grievance Cell",
}

DUPLICATE_SIMILARITY_THRESHOLD = 0.72

_models_cache = {}


def clean_text(text: str) -> str:
    """Same cleaning logic used during training (must stay consistent)."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _load_artifacts():
    """Lazily load model artifacts once and cache them in memory."""
    if _models_cache:
        return _models_cache

    required_files = [
        "tfidf_vectorizer.pkl",
        "category_model.pkl",
        "priority_model.pkl",
        "sentiment_model.pkl",
        "corpus_reference.pkl",
    ]
    for f in required_files:
        path = os.path.join(MODEL_DIR, f)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Model file '{f}' not found in {MODEL_DIR}. "
                f"Please run 'python train_model.py' first."
            )

    _models_cache["vectorizer"] = joblib.load(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))
    _models_cache["category_model"] = joblib.load(os.path.join(MODEL_DIR, "category_model.pkl"))
    _models_cache["priority_model"] = joblib.load(os.path.join(MODEL_DIR, "priority_model.pkl"))
    _models_cache["sentiment_model"] = joblib.load(os.path.join(MODEL_DIR, "sentiment_model.pkl"))
    _models_cache["corpus_reference"] = joblib.load(os.path.join(MODEL_DIR, "corpus_reference.pkl"))

    metrics_path = os.path.join(MODEL_DIR, "metrics.pkl")
    _models_cache["metrics"] = joblib.load(metrics_path) if os.path.exists(metrics_path) else {}

    return _models_cache


def get_model_metrics() -> dict:
    artifacts = _load_artifacts()
    return artifacts.get("metrics", {})


def _predict_with_confidence(model, vector):
    if not hasattr(model, "multi_class"):
        model.multi_class = "auto"

    proba = model.predict_proba(vector)[0]
    idx = int(np.argmax(proba))
    label = model.classes_[idx]
    confidence = float(proba[idx])
    return label, confidence


def analyze_complaint(complaint_text: str, existing_texts: list = None):
    """
    Full AI pipeline for a single complaint:
      1. Preprocess text
      2. Predict category
      3. Predict priority
      4. Predict sentiment
      5. Map category -> department
      6. Compute overall AI confidence score
      7. Detect duplicate complaints (against provided existing_texts,
         typically the current DB complaints, using cosine similarity)

    Returns a dict matching schemas.ComplaintAnalysisResult
    """
    artifacts = _load_artifacts()
    vectorizer = artifacts["vectorizer"]
    category_model = artifacts["category_model"]
    priority_model = artifacts["priority_model"]
    sentiment_model = artifacts["sentiment_model"]

    cleaned = clean_text(complaint_text)
    if not cleaned:
        cleaned = "general complaint"

    vector = vectorizer.transform([cleaned])

    category, cat_conf = _predict_with_confidence(category_model, vector)
    priority, pri_conf = _predict_with_confidence(priority_model, vector)
    sentiment, sent_conf = _predict_with_confidence(sentiment_model, vector)

    department = CATEGORY_DEPARTMENT_MAP.get(category, "General Grievance Cell")

    # Overall AI confidence = average of the three model confidences
    overall_confidence = round((cat_conf + pri_conf + sent_conf) / 3.0, 4)

    # --------------------------------------------------------------
    # Duplicate detection via TF-IDF cosine similarity
    # --------------------------------------------------------------
    is_duplicate = False
    duplicate_of = None
    similarity_score = 0.0

    if existing_texts:
        cleaned_existing = [clean_text(t) for t in existing_texts if t]
        if cleaned_existing:
            existing_vectors = vectorizer.transform(cleaned_existing)
            sims = cosine_similarity(vector, existing_vectors)[0]
            best_idx = int(np.argmax(sims))
            best_score = float(sims[best_idx])
            if best_score >= DUPLICATE_SIMILARITY_THRESHOLD:
                is_duplicate = True
                similarity_score = round(best_score, 4)
                duplicate_of = best_idx  # caller maps index -> ticket_id

    return {
        "category": category,
        "priority": priority,
        "department": department,
        "sentiment": sentiment,
        "confidence": overall_confidence,
        "is_duplicate": is_duplicate,
        "duplicate_of": duplicate_of,
        "similarity_score": similarity_score,
    }
