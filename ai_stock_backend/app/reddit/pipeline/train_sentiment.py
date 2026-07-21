from __future__ import annotations

import glob
import os
from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd
from joblib import dump
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from ..storage.paths import DATASET_DIR, ensure_dirs, DATA_DIR

LABEL_ORDER = ["neg", "neu", "pos"]  # fixed order for probabilities

@dataclass
class TrainArtifacts:
    vectorizer_path: str
    model_path: str

def _load_datasets(pattern: str = "*_weak_*.csv") -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(DATASET_DIR, pattern)))
    if not files:
        raise RuntimeError(f"No dataset files found in {DATASET_DIR}. Run export first.")
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    # keep only valid labels
    df = df[df["label"].isin(LABEL_ORDER)].copy()
    # drop empty / super short
    df["text"] = df["text"].fillna("").astype(str)
    df = df[df["text"].str.len() >= 10]
    return df

def train_and_save() -> TrainArtifacts:
    ensure_dirs()
    df = _load_datasets()

    X = df["text"].tolist()
    y = df["label"].tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        stop_words="english",
    )

    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    model = LogisticRegression(
        max_iter=200,
        class_weight="balanced",  # helps if labels are imbalanced
        multi_class="auto",
    )
    model.fit(X_train_vec, y_train)

    preds = model.predict(X_test_vec)
    print("Confusion matrix (rows=true, cols=pred):")
    print(confusion_matrix(y_test, preds, labels=LABEL_ORDER))
    print("\nClassification report:")
    print(classification_report(y_test, preds, labels=LABEL_ORDER))

    # Save artifacts
    out_dir = os.path.join(DATA_DIR, "models")
    os.makedirs(out_dir, exist_ok=True)

    vectorizer_path = os.path.join(out_dir, "reddit_vectorizer.joblib")
    model_path = os.path.join(out_dir, "reddit_sentiment_model.joblib")

    dump(vectorizer, vectorizer_path)
    dump(model, model_path)

    print("\nSaved:")
    print(vectorizer_path)
    print(model_path)

    return TrainArtifacts(vectorizer_path=vectorizer_path, model_path=model_path)

if __name__ == "__main__":
    train_and_save()
