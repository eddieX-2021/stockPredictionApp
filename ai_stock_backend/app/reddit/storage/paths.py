from __future__ import annotations
import os

# app/reddit/storage -> go to project/app/data/reddit
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "..", "..", "data", "reddit"))

RAW_DIR = os.path.join(DATA_DIR, "raw")
DB_PATH = os.path.join(DATA_DIR, "reddit.sqlite")
DATASET_DIR = os.path.join(DATA_DIR, "datasets")

def ensure_dirs():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(DATASET_DIR, exist_ok=True)
