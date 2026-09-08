"""
train_model.py
Trains the AI models for the Campus Helpdesk system:
  1. Category classifier   (TF-IDF + Logistic Regression)
  2. Priority classifier   (TF-IDF + Logistic Regression)
  3. Sentiment classifier  (TF-IDF + Logistic Regression)
  4. A shared TF-IDF vectorizer used later for duplicate detection

Saves all artifacts as .pkl files inside model/
Prints Accuracy, Precision, Recall, F1-score and Confusion Matrix for each model.
"""

import os
import re
import string

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "dataset", "complaints.csv")
MODEL_DIR = os.path.join(BASE_DIR, "model")
os.makedirs(MODEL_DIR, exist_ok=True)


def clean_text(text: str) -> str:
    """Basic text cleaning / preprocessing for NLP."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def train_and_evaluate(X_train, X_test, y_train, y_test, label_name, vectorizer):
    Xtr = vectorizer.transform(X_train)
    Xte = vectorizer.transform(X_test)

    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf.fit(Xtr, y_train)

    preds = clf.predict(Xte)

    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, average="weighted", zero_division=0)
    rec = recall_score(y_test, preds, average="weighted", zero_division=0)
    f1 = f1_score(y_test, preds, average="weighted", zero_division=0)
    cm = confusion_matrix(y_test, preds)

    print(f"\n===== {label_name} Model =====")
    print(f"Accuracy : {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall   : {rec:.4f}")
    print(f"F1-score : {f1:.4f}")
    print("Confusion Matrix:")
    print(cm)
    print("\nClassification Report:")
    print(classification_report(y_test, preds, zero_division=0))

    return clf, {
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1_score": f1,
        "confusion_matrix": cm.tolist(),
        "labels": sorted(list(set(y_test) | set(preds))),
    }


def main():
    print("Loading dataset from:", DATA_PATH)
    df = pd.read_csv(DATA_PATH)
    df = df.dropna(subset=["complaint_text", "category", "priority", "sentiment"])
    df["clean_text"] = df["complaint_text"].apply(clean_text)
    df = df[df["clean_text"].str.len() > 0]

    print(f"Total records after cleaning: {len(df)}")
    print(df[["category", "priority", "sentiment"]].apply(lambda c: c.value_counts()).fillna(0))

    # ------------------------------------------------------------------
    # Shared TF-IDF vectorizer (also reused at inference time for
    # duplicate detection via cosine similarity)
    # ------------------------------------------------------------------
    vectorizer = TfidfVectorizer(
        max_features=3000,
        ngram_range=(1, 2),
        stop_words="english",
        min_df=1,
    )
    vectorizer.fit(df["clean_text"])

    metrics = {}

    # ------------------------------------------------------------------
    # 1) Category classifier
    # ------------------------------------------------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        df["clean_text"], df["category"], test_size=0.2, random_state=42, stratify=df["category"]
    )
    category_model, cat_metrics = train_and_evaluate(
        X_train, X_test, y_train, y_test, "Category", vectorizer
    )
    metrics["category"] = cat_metrics

    # ------------------------------------------------------------------
    # 2) Priority classifier
    # ------------------------------------------------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        df["clean_text"], df["priority"], test_size=0.2, random_state=42, stratify=df["priority"]
    )
    priority_model, pri_metrics = train_and_evaluate(
        X_train, X_test, y_train, y_test, "Priority", vectorizer
    )
    metrics["priority"] = pri_metrics

    # ------------------------------------------------------------------
    # 3) Sentiment classifier
    # ------------------------------------------------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        df["clean_text"], df["sentiment"], test_size=0.2, random_state=42, stratify=df["sentiment"]
    )
    sentiment_model, sent_metrics = train_and_evaluate(
        X_train, X_test, y_train, y_test, "Sentiment", vectorizer
    )
    metrics["sentiment"] = sent_metrics

    # ------------------------------------------------------------------
    # Save artifacts
    # ------------------------------------------------------------------
    joblib.dump(vectorizer, os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))
    joblib.dump(category_model, os.path.join(MODEL_DIR, "category_model.pkl"))
    joblib.dump(priority_model, os.path.join(MODEL_DIR, "priority_model.pkl"))
    joblib.dump(sentiment_model, os.path.join(MODEL_DIR, "sentiment_model.pkl"))

    # Save the full training corpus TF-IDF matrix + texts for duplicate detection
    corpus_matrix = vectorizer.transform(df["clean_text"])
    joblib.dump(
        {
            "matrix": corpus_matrix,
            "texts": df["complaint_text"].tolist(),
        },
        os.path.join(MODEL_DIR, "corpus_reference.pkl"),
    )

    # Save metrics for display in admin analytics page
    joblib.dump(metrics, os.path.join(MODEL_DIR, "metrics.pkl"))

    print("\nAll models trained and saved successfully in:", MODEL_DIR)
    print("Files:", os.listdir(MODEL_DIR))


if __name__ == "__main__":
    main()
