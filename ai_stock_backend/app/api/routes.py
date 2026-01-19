from fastapi import APIRouter, Query, HTTPException
from app.mlm_predict.train_model import train_stock_models, get_model_cache
from app.services.fetch_data import fetch_raw_stock_data
from datetime import datetime, timedelta
import pytz

router = APIRouter()


@router.get("/")
def root():
    return {"message": "Welcome to the AI Stock Predictor API with Model Caching"}


@router.get("/predict")
async def predict(stock: str = Query(..., description="Stock ticker symbol (e.g., AAPL)")):
    """
    Predict stock movement using dual-model system (direction + magnitude).
    Automatically uses cached models when available.
    Returns: direction, confidence, percentage change, and predicted price.
    """
    eastern = pytz.timezone('US/Eastern')
    end_date = (datetime.now(eastern) - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=365*5)).strftime("%Y-%m-%d")
    
    ticker = stock.upper().strip()
    
    # Train models (or load from cache automatically)
    result = train_stock_models(ticker, start_date, end_date, verbose=False, use_cache=True)
    
    if result is None:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to train models for {ticker}. Check if ticker is valid."
        )
    
    # Get the latest features (today's data) for prediction
    latest_features = result["latest_features"]
    
    # Make prediction using the built-in predict function
    prediction = result["predict"](latest_features)
    
    # Fetch current price
    try:
        import yfinance as yf
        # Request last 5 days to ensure we catch the latest trading day (handles weekends/holidays)
        recent_data = yf.Ticker(ticker).history(period="5d")
        
        if recent_data is None or recent_data.empty:
             raise ValueError("No recent stock data found from Yahoo Finance")
             
        # Take the absolute latest closing price available
        current_price = float(recent_data['Close'].iloc[-1])
        
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}") # Log it for server logs
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch current price for {ticker}: {str(e)}"
        )
    
    # Extract prediction components
    direction = prediction["direction"]  # "UP" or "DOWN"
    direction_confidence = prediction["direction_confidence"]  # 0-1 (probability of UP)
    predicted_change_pct = prediction["final_prediction_pct"]  # Signed percentage change
    
    # Calculate predicted price
    predicted_price = current_price * (1 + predicted_change_pct / 100)
    
    # Format confidence based on direction
    if direction == "UP":
        confidence = direction_confidence
    else:
        confidence = 1 - direction_confidence
    
    return {
        "stock": ticker,
        "current_price": round(current_price, 2),
        "predicted_price": round(predicted_price, 2),
        "direction": direction,
        "confidence": round(confidence, 4),
        "predicted_change_pct": round(predicted_change_pct, 2),
        "system_confidence": result["confidence"],  # "high", "medium", or "low"
        "model_info": {
            "direction_model": result["direction"]["best_model_name"],
            "magnitude_model_up": result["magnitude"]["up"]["best_model_name"],
            "magnitude_model_down": result["magnitude"]["down"]["best_model_name"],
            "magnitude_model_used": prediction["magnitude_model_used"],  # Which one was actually used
            "cached": result["cached"]
        }
    }


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics and information"""
    model_cache = get_model_cache()
    stats = model_cache.get_stats()
    return {
        "message": "Model cache statistics",
        "stats": stats
    }


@router.post("/cache/clear-expired")
async def clear_expired_cache():
    """Clear expired cache entries (older than TTL)"""
    model_cache = get_model_cache()
    model_cache.clear_expired()
    stats = model_cache.get_stats()
    return {
        "message": "Expired cache cleared",
        "remaining_active": stats['active_models']
    }


@router.delete("/cache/ticker/{ticker}")
async def clear_ticker_cache(ticker: str):
    """Clear cache for a specific ticker (forces retrain on next request)"""
    ticker = ticker.upper()
    model_cache = get_model_cache()
    model_cache.clear_ticker(ticker)
    return {
        "message": f"Cache cleared for {ticker}",
        "note": "Next prediction request will retrain the model"
    }


@router.delete("/cache/clear-all")
async def clear_all_cache():
    """Clear entire cache (use with caution)"""
    model_cache = get_model_cache()
    model_cache.clear_all()
    return {
        "message": "All cache cleared",
        "warning": "All models will need to be retrained"
    }


@router.get("/cache/list")
async def list_cached_tickers():
    """List all currently cached tickers"""
    model_cache = get_model_cache()
    tickers = model_cache.list_cached_tickers()
    stats = model_cache.get_stats()
    return {
        "cached_tickers": tickers,
        "total": len(tickers),
        "details": stats['cached_tickers']
    }