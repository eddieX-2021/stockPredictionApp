from __future__ import annotations
import csv
from datetime import datetime
from ..storage.sqlite_store import SQLiteRedditStore
from ..storage.paths import DATASET_DIR, ensure_dirs
from ..nlp.text_clean import clean_text
from ..nlp.weak_label import weak_label

def export_weak_labeled_dataset(ticker: str, limit: int = 5000) -> str:
    """
    Day 1: generate a training dataset using weak labels (VADER).
    Later we’ll replace/augment these labels with better labeling.
    """
    ensure_dirs()
    store = SQLiteRedditStore()
    rows = store.fetch_comments_for_ticker(ticker.upper(), limit=limit)

    out_path = f"{DATASET_DIR}/{ticker.upper()}_weak_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["comment_id", "post_id", "ticker", "text", "score", "created_utc", "permalink", "label", "compound"])

        for (comment_id, post_id, ticker, body, score, created_utc, permalink) in rows:
            text = clean_text(body)
            if len(text) < 10:
                continue
            lab = weak_label(text)
            w.writerow([comment_id, post_id, ticker, text, score, created_utc, permalink, lab.label, lab.compound])

    return out_path
