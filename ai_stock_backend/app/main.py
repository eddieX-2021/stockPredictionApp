# FastAPI app entrypoint
from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="AI Stock Predictor",
    description="Predict stock price movement and analyze sentiment.",
    version="1.0.0"
)

app.include_router(router)
