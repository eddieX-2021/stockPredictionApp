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

# financial statement endpoint
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

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://stock-prediction-app-two.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^http:\/\/localhost:\d+$|^http:\/\/127\.0\.0\.1:\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# include any externally defined routes
app.include_router(router)


# ─── /api/news ───────────────────────────────────────────────────────────────
@app.post("/api/news")
async def news_sentiment(req: TickerRequest):
    t = req.ticker.strip().upper()
    
    try:
        headlines = get_top_headlines(t)
        
        # Handle empty headlines gracefully
        if not headlines or len(headlines) == 0:
            print(f"No news headlines found for {t}")
            return {
                "ticker": t,
                "news": [],
                "message": "No recent news articles found"
            }
        
        sentiments = predict_news_sentiments(headlines)
        
        return {
            "ticker": t,
            "news": [
                {"headline": h, "sentiment": s}
                for h, s in zip(headlines, sentiments)
            ]
        }
    except Exception as e:
        print(f"Error in news_sentiment for {t}: {e}")
        # Return empty results instead of crashing
        return {
            "ticker": t,
            "news": [],
            "error": "Unable to fetch news at this time"
        }


# ─── /api/reddit ─────────────────────────────────────────────────────────────
@app.post("/api/reddit")
async def reddit_sentiment(req: TickerRequest):
    t = req.ticker.strip().upper()
    
    try:
        posts = fetch_reddit(t)
        
        if not posts or len(posts) == 0:
            print(f"⚠️ No Reddit posts found for {t}")
            return {
                "ticker": t,
                "reddit": [],
                "message": "No recent Reddit discussions found"
            }
        
        sentiments = predict_reddit_sentiments(posts)
        
        return {
            "ticker": t,
            "reddit": [
                {"post": p, "sentiment": s}
                for p, s in zip(posts, sentiments)
            ]
        }
    except Exception as e:
        print(f"Error in reddit_sentiment for {t}: {e}")
        return {
            "ticker": t,
            "reddit": [],
            "error": "Unable to fetch Reddit data at this time"
        }


from app.services.json_safe import json_safe

@app.post("/api/financials")
async def financials(req: TickerRequest):
    t = req.ticker.strip().upper()

    try:
        fin_data = fetch_financials(t)
        direction, confidence = predict_stock_movement(t, fin_data)
    except Exception as e:
        print(f" Error in financials for {t}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    response = {
        "ticker": t,
        "financials": fin_data,
        "direction": direction,
        "confidence": confidence,
    }

    # THIS PREVENTS THE CRASH
    return json_safe(response)


# ─── CLI / TRAIN (optional) ──────────────────────────────────────────────────
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