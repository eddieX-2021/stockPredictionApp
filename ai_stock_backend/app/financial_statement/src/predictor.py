import pandas as pd
import joblib
from pathlib import Path
from .fetch_fin import fetch_financials

def predict_stock_movement(ticker: str) -> tuple[str, float]:
    """
    Returns (direction, confidence) for the given ticker,
    where direction is "UP" or "DOWN" and confidence is a float [0,1].
    """
    # ── locate model artifact ─────────────────────────────────────────
    HERE     = Path(__file__).resolve().parent
    FIN_ROOT = HERE.parent
    MODEL_F  = FIN_ROOT / "models" / "stock_dir_model_logreg_tuned.pkl"
    if not MODEL_F.exists():
        raise FileNotFoundError(f"Model not found at {MODEL_F}")

    # ── load model + feature list ──────────────────────────────────────
    art      = joblib.load(MODEL_F)
    model    = art["model"]
    features = art["features"]          # e.g. ["TotalRevenue_chg", ...]
    raw_feats = [f[:-4] for f in features]

    # ── fetch the two most-recent years of financials ──────────────────
    fin = fetch_financials(ticker)
    latest = fin["latest"]
    prev   = fin["prev"]

    # ── compute year-over-year growth for each feature ────────────────
    growth = {}
    for feat, raw in zip(features, raw_feats):
        v2 = latest.get(raw)
        v1 = prev.get(raw)
        if v1 in (0, None) or v2 is None:
            growth[feat] = 0.0
        else:
            growth[feat] = (v2 - v1) / v1

    Xnew = pd.DataFrame([growth])

    # ── predict direction + probability ───────────────────────────────
    pred = model.predict(Xnew)[0]
    prob = model.predict_proba(Xnew)[0, int(pred)]

    direction = "UP" if pred == 1 else "DOWN"
    return direction, float(prob)