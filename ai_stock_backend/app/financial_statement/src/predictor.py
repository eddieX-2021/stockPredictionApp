# predictor.py
import pandas as pd
import joblib
from pathlib import Path
from fetch_fin import fetch_financials

def predict_direction(ticker: str):
    # Paths
    HERE      = Path(__file__).resolve().parent
    FIN_ROOT  = HERE.parent
    MODEL_F   = FIN_ROOT / "models" / "stock_dir_model_logreg_tuned.pkl"
    if not MODEL_F.exists():
        print("ERROR: model file not found at", MODEL_F)
        return

    # Load model + feature list
    art      = joblib.load(MODEL_F)
    model    = art["model"]
    features = art["features"]  # e.g. ["TotalRevenue_chg", ...]
    raw_feats = [f[:-4] for f in features]

    # Fetch financials via yfinance
    try:
        fin = fetch_financials(ticker)
    except Exception as e:
        print("❌ Fetch error:", e)
        return

    latest = fin["latest"]
    prev   = fin["prev"]

    # Build YoY–growth vector
    growth = {}
    for feat, raw in zip(features, raw_feats):
        v2 = latest.get(raw)
        v1 = prev.get(raw)
        if v1 in (0, None) or v2 is None:
            growth[feat] = 0.0
        else:
            growth[feat] = (v2 - v1) / v1

    Xnew = pd.DataFrame([growth])

    # Predict
    try:
        pred = model.predict(Xnew)[0]
        prob = model.predict_proba(Xnew)[0, int(pred)]
    except Exception as e:
        print("❌ Prediction error:", e)
        return

    direction = "UP" if pred == 1 else "DOWN"
    print(f"{ticker.upper()} → {direction} (conf {prob:.1%})")
