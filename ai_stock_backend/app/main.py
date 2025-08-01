from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# include any additional routers
from app.api.routes import router

# sentiment endpoints
from app.headline.src.fetch_news import get_top_headlines
from app.headline.src.predictor import predict_sentiments as predict_news_sentiments
from app.reddit.src.fetch_reddit import fetch_reddit
from app.reddit.src.predictor import predict_sentiments as predict_reddit_sentiments

# financial‐statement endpoint
from app.financial_statement.src.fetch_fin import fetch_financials
from app.financial_statement.src.predictor import predict_stock_movement

# CLI/train functionality
from app.services.fetch_data import fetch_raw_stock_data, generate_features
from app.mlm_predict.train_model import train_stock_models
from datetime import datetime, timedelta
import pytz


class TickerRequest(BaseModel):
    ticker: str


app = FastAPI(
    title="AI Stock Predictor",
    description="Predict stock price movement and analyze sentiment.",
    version="1.0.0"
)

# ─── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # your Next.js origin
    allow_credentials=True,
    allow_methods=["*"],  # allow GET, POST, etc.
    allow_headers=["*"],
)

# include any externally defined routes
app.include_router(router)


# ─── /api/news ────────────────────────────────────────────────────
@app.post("/api/news")
async def news_sentiment(req: TickerRequest):
    t = req.ticker.strip().upper()
    headlines = get_top_headlines(t)
    sentiments = predict_news_sentiments(headlines)
    return {
        "ticker": t,
        "news": [
            {"headline": h, "sentiment": s}
            for h, s in zip(headlines, sentiments)
        ]
    }


# ─── /api/reddit ──────────────────────────────────────────────────
@app.post("/api/reddit")
async def reddit_sentiment(req: TickerRequest):
    t = req.ticker.strip().upper()
    posts = fetch_reddit(t)
    sentiments = predict_reddit_sentiments(posts)
    return {
        "ticker": t,
        "reddit": [
            {"post": p, "sentiment": s}
            for p, s in zip(posts, sentiments)
        ]
    }


@app.post("/api/financials")
async def financials(req: TickerRequest):
    t = req.ticker.strip().upper()

    # 1) fetch raw financial data
    try:
        fin_data = fetch_financials(t)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Financial fetch failed: {e}")

    # 2) get direction & confidence
    try:
        direction, confidence = predict_stock_movement(t)
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=500, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")

    # 3) return everything
    return {
        "ticker": t,
        "financials": fin_data,
        "direction": direction,    # "UP" or "DOWN"
        "confidence": confidence,  # 0.0–1.0 float
    }


# ─── CLI / TRAIN (optional) ────────────────────────────────────────
def main():
    eastern = pytz.timezone('US/Eastern')
    end_date = (datetime.now(eastern) - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (
        datetime.strptime(end_date, "%Y-%m-%d")
        - timedelta(days=90)
    ).strftime("%Y-%m-%d")
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
