import pandas as pd
import joblib
from pathlib import Path

def predict_stock_movement(ticker: str, fin: dict) -> tuple[str, float]:
    """
    Predict stock direction using PRE-FETCHED financials.
    """

    # ─────────────────────────────────────────────
    # Load trained model ONCE per process
    # ─────────────────────────────────────────────
    HERE = Path(__file__).resolve().parent
    MODEL_F = HERE.parent / "models" / "stock_dir_model_logreg_tuned.pkl"

    if not MODEL_F.exists():
        raise FileNotFoundError(f"Model not found at {MODEL_F}")

    artifact = joblib.load(MODEL_F)
    model = artifact["model"]
    features = artifact["features"]

    latest = fin["latest"]
    prev = fin["prev"]

    # ─────────────────────────────────────────────
    # Compute year-over-year growth
    # ─────────────────────────────────────────────
    growth = {}

    for feat in features:
        raw = feat.replace("_chg", "")
        v2 = latest.get(raw)
        v1 = prev.get(raw)

        if v1 in (0, None) or v2 is None:
            growth[feat] = 0.0
        else:
            growth[feat] = (v2 - v1) / v1

    X = pd.DataFrame([growth])

    # ─────────────────────────────────────────────
    # Predict
    # ─────────────────────────────────────────────
    pred = model.predict(X)[0]
    prob = model.predict_proba(X)[0, int(pred)]

    direction = "UP" if pred == 1 else "DOWN"
    return direction, float(prob)
