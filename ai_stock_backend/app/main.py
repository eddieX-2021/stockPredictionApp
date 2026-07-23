import os
from datetime import datetime, timedelta

import pytz
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.routes import router
from app.mlm_predict.train_model import train_stock_models
from app.services.fetch_data import fetch_raw_stock_data, generate_features
from app.services.json_safe import json_safe


class TickerRequest(BaseModel):
    ticker: str


app = FastAPI(
    title="Equity Research Dashboard API",
    description="Phase 1 stock research dashboard API with price, financial, risk, sentiment, and experimental prediction signals.",
    version="1.0.0",
)

# CORS
_default_origins = [
    "https://stock-prediction-app-two.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_extra_origins = [origin.strip() for origin in os.getenv("FRONTEND_ORIGINS", "").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[*_default_origins, *_extra_origins],
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$|^http:\/\/localhost:\d+$|^http:\/\/127\.0\.0\.1:\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.post("/api/news")
async def news_sentiment(req: TickerRequest):
    t = req.ticker.strip().upper()

    try:
        from app.headline.src.fetch_news import get_top_headlines
        from app.headline.src.predictor import predict_sentiments as predict_news_sentiments

        headlines = get_top_headlines(t)

        if not headlines:
            print(f"No news headlines found for {t}")
            return {
                "ticker": t,
                "news": [],
                "message": "No recent news articles found",
            }

        sentiments = predict_news_sentiments(headlines)

        return {
            "ticker": t,
            "news": [
                {"headline": h, "sentiment": s}
                for h, s in zip(headlines, sentiments)
            ],
        }
    except Exception as e:
        print(f"Error in news_sentiment for {t}: {e}")
        return {
            "ticker": t,
            "news": [],
            "error": "Unable to fetch news at this time",
        }


@app.post("/api/reddit")
async def reddit_sentiment(req: TickerRequest):
    t = req.ticker.strip().upper()
    return {
        "ticker": t,
        "reddit": [],
        "disabled": True,
        "message": "Live Reddit sentiment is disabled to avoid token/rate-limit crashes.",
    }


@app.post("/api/financials")
async def financials(req: TickerRequest):
    t = req.ticker.strip().upper()

    try:
        from app.financial_statement.src.fetch_fin import fetch_financials
        from app.financial_statement.src.predictor import predict_stock_movement

        fin_data = fetch_financials(t)
        direction, confidence = predict_stock_movement(t, fin_data)
    except Exception as e:
        print(f"Error in financials for {t}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    response = {
        "ticker": t,
        "financials": fin_data,
        "direction": direction,
        "confidence": confidence,
    }

    return json_safe(response)


# CLI / train helper (optional)
def main():
    eastern = pytz.timezone("US/Eastern")
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

    result = train_stock_models(ticker, start_date, end_date)
    if result is None:
        print(f"Failed to train model for {ticker}")
        return

    print(f"Trained model for {ticker}, ready for prediction via /predict endpoint")


if __name__ == "__main__":
    main()