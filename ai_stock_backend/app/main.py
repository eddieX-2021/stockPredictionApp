# FastAPI app entrypoint
from fastapi import FastAPI
from app.api.routes import router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Stock Predictor",
    description="Predict stock price movement and analyze sentiment.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # your Next app URL
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

from app.headline.src.fetch_news   import get_top_headlines
from app.headline.src.predictor    import predict_sentiments
@app.get("/sentiment/{company}")
def sentiment(company: str):
    headlines = get_top_headlines(company)
    preds     = predict_sentiments(headlines)
    return [{"headline":h, "sentiment":s} for h,s in zip(headlines, preds)]

app.include_router(router)
