# FastAPI app entrypoint
from fastapi import FastAPI
from app.api.routes import router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Stock Predictor",
    description="Predict stock price movement and analyze sentiment.",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

app.include_router(router)


from app.services.fetch_data import fetch_raw_stock_data, generate_features
from app.mlm_predict.train_model import train_stock_models
from datetime import datetime, timedelta
import pytz

def main():
    eastern = pytz.timezone('US/Eastern')
    end_date = (datetime.now(eastern) - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")
    ticker = "AAPL"

    stock_data = fetch_raw_stock_data(ticker, start_date, end_date)
    if stock_data is None:
        print(f"Failed to fetch data for {ticker}")
        return
    X, y, _ = generate_features(stock_data)
    if X is None or y is None:
        print(f"Failed to generate features for {ticker}")
        return

    best_model, scaler = train_stock_models(ticker, start_date, end_date)
    if best_model is None or scaler is None:
        print(f"Failed to train model for {ticker}")
        return

    print(f"Trained model for {ticker}, ready for prediction via /predict endpoint")

if __name__ == "__main__":
    main()
