import re
from datetime import datetime, timedelta

import pytz
from fastapi import APIRouter, Query, HTTPException, Request

from app.mlm_predict.train_model import train_stock_models, get_model_cache
from app.services.fetch_data import fetch_raw_stock_data
from app.services.analysis import build_stock_analysis
from app.services.analysis_cache import (
    clear_analysis_cache,
    clear_expired_analysis_cache,
    get_analysis_cache_stats,
    get_or_build_analysis,
)
from app.services.mcp_tools import MCP_TOOLS, SERVER_INFO, handle_mcp_request

router = APIRouter()
TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")


def normalize_ticker_symbol(stock: str) -> str:
    ticker = stock.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    if not TICKER_PATTERN.fullmatch(ticker):
        raise HTTPException(
            status_code=400,
            detail="Ticker must be 1-10 characters and contain only letters, numbers, dots, or hyphens.",
        )
    return ticker


@router.get("/")
def root():
    return {"message": "Welcome to the Equity Research Dashboard API"}


@router.get("/analysis")
@router.get("/api/analysis")
async def analysis(
    stock: str = Query(..., description="Stock ticker symbol (e.g., AAPL)"),
    force_refresh: bool = Query(False, description="Bypass SQLite cache and rebuild analysis"),
):
    """
    Unified Phase 1 stock analysis endpoint with SQLite caching.

    Cached responses reduce repeated calls to free public data providers.
    Use force_refresh=true while testing a fresh rebuild.
    """
    ticker = normalize_ticker_symbol(stock)
    return get_or_build_analysis(ticker, build_stock_analysis, force_refresh=force_refresh)


@router.get("/analysis-cache/stats")
async def analysis_cache_stats():
    """Get SQLite analysis cache statistics."""
    return get_analysis_cache_stats()


@router.post("/analysis-cache/clear-expired")
async def analysis_cache_clear_expired():
    """Clear expired analysis cache entries."""
    removed = clear_expired_analysis_cache()
    return {"message": "Expired analysis cache cleared", "removed": removed}


@router.delete("/analysis-cache/ticker/{ticker}")
async def analysis_cache_clear_ticker(ticker: str):
    """Clear cached analysis for one ticker."""
    normalized = normalize_ticker_symbol(ticker)
    removed = clear_analysis_cache(normalized)
    return {"message": f"Analysis cache cleared for {normalized}", "removed": removed}


@router.delete("/analysis-cache/clear-all")
async def analysis_cache_clear_all():
    """Clear all cached analysis responses."""
    removed = clear_analysis_cache()
    return {"message": "All analysis cache entries cleared", "removed": removed}


@router.get("/mcp")
async def mcp_info():
    """
    Lightweight MCP info endpoint.

    ChatGPT connector setup should use POST /mcp as the connector URL.
    """
    return {
        "server": SERVER_INFO,
        "endpoint": "/mcp",
        "transport": "streamable-http-json-rpc",
        "tools": [tool["name"] for tool in MCP_TOOLS],
    }


@router.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    Lightweight MCP-compatible JSON-RPC endpoint for local/free stock analysis tools.

    Supports initialize, tools/list, and tools/call.
    """
    payload = await request.json()
    return handle_mcp_request(payload)


@router.get("/predict")
async def predict(stock: str = Query(..., description="Stock ticker symbol (e.g., AAPL)")):
    """
    Predict stock movement using dual-model system (direction + magnitude).
    Automatically uses cached models when available.
    Returns: direction, confidence, percentage change, and predicted price.
    """
    eastern = pytz.timezone("US/Eastern")
    end_date = (datetime.now(eastern) - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=365 * 5)).strftime("%Y-%m-%d")

    ticker = normalize_ticker_symbol(stock)

    # Train models (or load from cache automatically)
    result = train_stock_models(ticker, start_date, end_date, verbose=False, use_cache=True)

    if result is None:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to train models for {ticker}. Check if ticker is valid.",
        )

    # Get the latest features (today's data) for prediction
    latest_features = result["latest_features"]

    # Make prediction using the built-in predict function
    prediction = result["predict"](latest_features)

    # Fetch current price
    try:
        price_start = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")
        stock_data = fetch_raw_stock_data(ticker, price_start, end_date)
        if stock_data is None or stock_data.empty:
            raise ValueError("No stock data available")
        current_price = float(stock_data["Close"].iloc[-1])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch current price for {ticker}: {str(e)}",
        )

    # Extract prediction components
    direction = prediction["direction"]
    direction_confidence = prediction["direction_confidence"]
    predicted_change_pct = prediction["final_prediction_pct"]

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
        "system_confidence": result["confidence"],
        "model_info": {
            "direction_model": result["direction"]["best_model_name"],
            "magnitude_model": result["magnitude"]["best_model_name"],
            "cached": result["cached"],
        },
    }


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics and information"""
    model_cache = get_model_cache()
    stats = model_cache.get_stats()
    return {
        "message": "Model cache statistics",
        "stats": stats,
    }


@router.post("/cache/clear-expired")
async def clear_expired_cache():
    """Clear expired cache entries (older than TTL)"""
    model_cache = get_model_cache()
    model_cache.clear_expired()
    stats = model_cache.get_stats()
    return {
        "message": "Expired cache cleared",
        "remaining_active": stats["active_models"],
    }


@router.delete("/cache/ticker/{ticker}")
async def clear_ticker_cache(ticker: str):
    """Clear cache for a specific ticker (forces retrain on next request)"""
    normalized = normalize_ticker_symbol(ticker)
    model_cache = get_model_cache()
    model_cache.clear_ticker(normalized)
    return {
        "message": f"Cache cleared for {normalized}",
        "note": "Next prediction request will retrain the model",
    }


@router.delete("/cache/clear-all")
async def clear_all_cache():
    """Clear entire cache (use with caution)"""
    model_cache = get_model_cache()
    model_cache.clear_all()
    return {
        "message": "All cache cleared",
        "warning": "All models will need to be retrained",
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
        "details": stats["cached_tickers"],
    }