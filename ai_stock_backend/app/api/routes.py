from fastapi import APIRouter, Query, HTTPException
from app.mlm_predict.train_model import train_stock_models
from app.mlm_predict.model_cache import ModelCache
from app.services.fetch_data import fetch_raw_stock_data, generate_features
from datetime import datetime, timedelta
import pytz

router = APIRouter()

# Initialize persistent model cache (survives across requests)
# TTL = 7 days (models retrain weekly)
model_cache = ModelCache(cache_dir="model_cache", cache_duration_days=7)


@router.get("/")
def root():
    return {"message": "Welcome to the AI Stock Predictor API with Model Caching"}


@router.get("/predict")
async def predict(stock: str = Query(..., description="Stock ticker symbol (e.g., AAPL)")):
    """
    Predict stock movement using dual-model system (direction + magnitude).
    Uses cached models when available to avoid retraining.
    Returns: direction, confidence, percentage change, and predicted price.
    """
    eastern = pytz.timezone('US/Eastern')
    end_date = (datetime.now(eastern) - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=365*5)).strftime("%Y-%m-%d")
    
    ticker = stock.upper().strip()
    
    # Try to load from persistent cache first
    result = model_cache.get(ticker)
    
    if result is None:
        # No cache found or cache expired - need to train
        print(f"[TRAINING] Training new models for {ticker}... (this may take 15-45 seconds)")
        
        # Train the dual-model system
        result = train_stock_models(ticker, start_date, end_date, verbose=False)
        
        if result is None:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to train models for {ticker}. Check if ticker is valid."
            )
        
        # Save to persistent cache
        model_cache.save(ticker, result)
        print(f"[CACHE] ✓ Models trained and cached for {ticker}")
        was_cached = False
    else:
        # Using cached model
        print(f"[CACHE] ✓ Using cached model for {ticker}")
        was_cached = True
    
    # Get the latest features (today's data) for prediction
    latest_features = result["latest_features"]
    
    # Make prediction using the built-in predict function
    prediction = result["predict"](latest_features)
    
    # Fetch current price (need at least 50 trading days, ~75 calendar days to be safe)
    try:
        price_start = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")
        stock_data = fetch_raw_stock_data(ticker, price_start, end_date)
        if stock_data is None or stock_data.empty:
            raise ValueError("No stock data available")
        current_price = float(stock_data['Close'].iloc[-1])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch current price for {ticker}: {str(e)}"
        )
    
    # Extract prediction components
    direction = prediction["direction"]  # "UP" or "DOWN"
    direction_confidence = prediction["direction_confidence"]  # 0-1 (probability of UP)
    predicted_change_pct = prediction["final_prediction_pct"]  # Signed percentage change
    
    # Calculate predicted price
    # Formula: current_price * (1 + predicted_change_pct/100)
    predicted_price = current_price * (1 + predicted_change_pct / 100)
    
    # Format confidence based on direction
    # If direction is UP, confidence = direction_confidence
    # If direction is DOWN, confidence = 1 - direction_confidence
    if direction == "UP":
        confidence = direction_confidence
    else:
        confidence = 1 - direction_confidence
    
    return {
        "stock": ticker,
        "current_price": round(current_price, 2),
        "predicted_price": round(predicted_price, 2),
        "direction": direction,
        "confidence": round(confidence, 4),  # 0-1 scale
        "predicted_change_pct": round(predicted_change_pct, 2),
        "system_confidence": result["confidence"],  # "high", "medium", or "low"
        "model_info": {
            "direction_model": result["direction"]["best_model_name"],
            "magnitude_model": result["magnitude"]["best_model_name"],
            "cached": was_cached
        }
    }


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics and information"""
    stats = model_cache.get_stats()
    return {
        "message": "Model cache statistics",
        "stats": stats
    }


@router.post("/cache/clear-expired")
async def clear_expired_cache():
    """Clear expired cache entries (older than TTL)"""
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
    model_cache.clear_ticker(ticker)
    return {
        "message": f"Cache cleared for {ticker}",
        "note": "Next prediction request will retrain the model"
    }


@router.delete("/cache/clear-all")
async def clear_all_cache():
    """Clear entire cache (use with caution)"""
    model_cache.clear_all()
    return {
        "message": "All cache cleared",
        "warning": "All models will need to be retrained"
    }


@router.get("/cache/list")
async def list_cached_tickers():
    """List all currently cached tickers"""
    tickers = model_cache.list_cached_tickers()
    stats = model_cache.get_stats()
    return {
        "cached_tickers": tickers,
        "total": len(tickers),
        "details": stats['cached_tickers']
    }