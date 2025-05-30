# FastAPI route definitions
from fastapi import APIRouter, Query
# from app.models.stock_model import predict_stock_movement
# from app.models.sentiment_model import analyze_sentiment

router = APIRouter()

# @router.get("/predict")
# def predict(stock: str = Query(...)):
    # stock_pred = predict_stock_movement(stock)
    # sentiment = analyze_sentiment(stock)
    # return {"stock_prediction": stock_pred, "sentiment": sentiment}

# test
@router.get("/")
def root():
    return {"message": "Welcome to the AI Stock Predictor API"}
