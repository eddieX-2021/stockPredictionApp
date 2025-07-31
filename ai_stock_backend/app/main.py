from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# import your existing logic
from app.headline.src.fetch_news   import get_top_headlines
from app.headline.src.predictor    import predict_sentiments as predict_news_sentiments
from app.reddit.src.fetch_reddit   import fetch_reddit
from app.reddit.src.predictor      import predict_sentiments as predict_reddit_sentiments
from app.financial_statement.src.fetch_fin import fetch_financials
from app.financial_statement.src.predictor_stock import (
    predict_stock_movement,
    get_model_accuracy
)

class TickerRequest(BaseModel):
    ticker: str

app = FastAPI(
    title="AI Stock Predictor",
    description="Predict stock price movement and analyze sentiment.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # adjust if your frontend runs elsewhere
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

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
    # your existing Yahoo‐Finance wrapper
    try:
        fin_data = fetch_financials(t)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    # your price‐prediction functions
    movement = predict_stock_movement(t)
    accuracy = get_model_accuracy()
    return {
        "ticker": t,
        "financials": fin_data,
        "prediction": movement,      # e.g. "up" or "down"
        "accuracy": accuracy        # e.g. 0.78
    }
