from fastapi import APIRouter, Query
from app.mlm_predict.train_model import train_stock_models
from app.services.fetch_data import fetch_raw_stock_data, generate_features
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import pandas as pd
from datetime import datetime, timedelta
import pytz

router = APIRouter()
model_cache = {}

@router.get("/")
def root():
    return {"message": "Welcome to the AI Stock Predictor API"}

@router.get("/predict")
async def predict(stock: str = Query(..., description="Stock ticker symbol (e.g., AAPL)")):
    eastern = pytz.timezone('US/Eastern')
    end_date = (datetime.now(eastern) - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")

    if stock not in model_cache:
        stock_data = fetch_raw_stock_data(stock, start_date, end_date)
        if stock_data is None:
            return {"error": f"Failed to fetch data for {stock}"}

        X, y, stock_data = generate_features(stock_data)
        if X is None or y is None:
            return {"error": f"Failed to generate features for {stock}"}

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        best_model, scaler = train_stock_models(stock, start_date, end_date)
        if best_model is None or scaler is None:
            return {"error": f"Failed to train model for {stock}"}
        model_cache[stock] = {"model": best_model, "scaler": scaler}

    stock_data = fetch_raw_stock_data(stock, start_date, end_date)
    if stock_data is None:
        return {"error": f"Failed to fetch data for {stock}"}

    X, _, _ = generate_features(stock_data)
    if X is None:
        return {"error": f"Failed to generate features for {stock}"}

    latest_features = X.iloc[-1].values.reshape(1, -1)
    latest_features_scaled = model_cache[stock]["scaler"].transform(latest_features)
    prediction = model_cache[stock]["model"].predict(latest_features_scaled)[0]

    return {"stock": stock, "predicted_price": round(prediction, 2)}