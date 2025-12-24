"""
Stock Prediction Testing Script

USAGE GUIDE:
------------
To make predictions on new data:

    from app.mlm_predict.train_model import train_stock_models
    
    # Train models
    result = train_stock_models(ticker, start_date, end_date)
    
    # Make prediction
    prediction = make_prediction(result, X_new)
    
    print(f"Direction: {prediction['direction']}")
    print(f"Confidence: {prediction['direction_confidence']:.2%}")
    print(f"Expected Change: {prediction['magnitude_pct']:.2f}%")

INTERPRETATION:
---------------
Direction Prediction:
  • UP/DOWN: Predicted movement for next trading day
  • Confidence: Probability (0.5-1.0, higher is better)
    - > 0.7: Strong signal
    - 0.6-0.7: Moderate signal
    - 0.5-0.6: Weak signal

Magnitude Prediction:
  • Shows expected % change (positive or negative)
  • Consider this alongside direction for complete picture
  • MAE in test results shows typical prediction error

Overall Confidence:
  • HIGH: Both models performing well, reliable predictions
  • MEDIUM: Decent performance, use with caution
  • LOW: Uncertain predictions, consider external factors
"""

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from app.mlm_predict.train_model import (train_stock_models, 
                                          predict_ensemble_direction, 
                                          predict_ensemble_magnitude)


def make_prediction(result, X_new):
    """
    Make a complete prediction using both direction and magnitude models.
    
    Args:
        result: Output from train_stock_models
        X_new: Feature array for prediction (single row or multiple rows)
    
    Returns:
        Dictionary with predictions and confidence
    """
    dir_info = result["direction"]
    mag_info = result["magnitude"]
    
    # Use ensemble if available, otherwise use best single model
    if dir_info["ensemble"]:
        direction_pred, direction_prob = predict_ensemble_direction(X_new, dir_info["ensemble"])
    else:
        X_proc = dir_info["scaler"].transform(X_new) if dir_info["scaler"] else X_new
        direction_pred = dir_info["best_model"].predict(X_proc)
        if hasattr(dir_info["best_model"], "predict_proba"):
            direction_prob = dir_info["best_model"].predict_proba(X_proc)[:, 1]
        else:
            direction_prob = direction_pred
    
    if mag_info["ensemble"]:
        magnitude_pred = predict_ensemble_magnitude(X_new, mag_info["ensemble"])
    else:
        X_proc = mag_info["scaler"].transform(X_new) if mag_info["scaler"] else X_new
        magnitude_pred = mag_info["best_model"].predict(X_proc)
    
    return {
        "direction": ["DOWN", "UP"][direction_pred[0]] if len(direction_pred) == 1 else direction_pred,
        "direction_confidence": direction_prob[0] if len(direction_prob) == 1 else direction_prob,
        "magnitude_pct": magnitude_pred[0] if len(magnitude_pred) == 1 else magnitude_pred,
        "using_ensemble": {
            "direction": dir_info["ensemble"] is not None,
            "magnitude": mag_info["ensemble"] is not None
        }
    }


def test_single_ticker(ticker, start_date, end_date):
    """Test a single ticker and return results."""
    print(f"\n{'='*70}")
    print(f"Testing: {ticker}")
    print(f"{'='*70}")
    
    result = train_stock_models(ticker, start_date, end_date)
    
    if result:
        dir_info = result["direction"]
        mag_info = result["magnitude"]
        confidence = result["confidence"]
        
        # Compile summary
        summary = {
            "ticker": ticker,
            "confidence": confidence,
            "direction_model": dir_info['best_model_name'],
            "direction_accuracy": dir_info['metrics']['test']['Accuracy'],
            "direction_f1": dir_info['metrics']['test']['F1'],
            "direction_precision": dir_info['metrics']['test']['Precision'],
            "direction_recall": dir_info['metrics']['test']['Recall'],
            "magnitude_model": mag_info['best_model_name'],
            "magnitude_r2": mag_info['metrics']['test']['R²'],
            "magnitude_mae": mag_info['metrics']['test']['MAE'],
            "magnitude_rmse": mag_info['metrics']['test']['RMSE'],
            "has_dir_ensemble": dir_info["ensemble"] is not None,
            "has_mag_ensemble": mag_info["ensemble"] is not None
        }
        
        return result, summary
    
    return None, None


def print_summary_table(summaries):
    """Print a compact summary table of all tested tickers."""
    if not summaries:
        return
    
    df = pd.DataFrame(summaries)
    
    print("\n" + "="*100)
    print("MULTI-TICKER SUMMARY")
    print("="*100)
    
    # Direction models summary
    print("\nDIRECTION MODELS:")
    print("-" * 100)
    print(f"{'Ticker':<8} {'Model':<20} {'Accuracy':<10} {'F1':<8} {'Precision':<10} {'Recall':<8} {'Ensemble':<10}")
    print("-" * 100)
    
    for _, row in df.iterrows():
        print(f"{row['ticker']:<8} {row['direction_model']:<20} "
              f"{row['direction_accuracy']:.4f}     {row['direction_f1']:.4f}   "
              f"{row['direction_precision']:.4f}     {row['direction_recall']:.4f}   "
              f"{'Yes' if row['has_dir_ensemble'] else 'No':<10}")
    
    # Magnitude models summary
    print("\nMAGNITUDE MODELS:")
    print("-" * 100)
    print(f"{'Ticker':<8} {'Model':<20} {'R²':<10} {'MAE':<10} {'RMSE':<10} {'Ensemble':<10}")
    print("-" * 100)
    
    for _, row in df.iterrows():
        print(f"{row['ticker']:<8} {row['magnitude_model']:<20} "
              f"{row['magnitude_r2']:.4f}     {row['magnitude_mae']:.3f}%     "
              f"{row['magnitude_rmse']:.3f}%     {'Yes' if row['has_mag_ensemble'] else 'No':<10}")
    
    # Overall summary
    print("\nOVERALL CONFIDENCE:")
    print("-" * 100)
    print(f"{'Ticker':<8} {'Confidence':<15} {'Notes'}")
    print("-" * 100)
    
    for _, row in df.iterrows():
        notes = []
        if row['direction_accuracy'] > 0.55:
            notes.append("Good direction")
        if row['magnitude_r2'] > 0.1:
            notes.append("Good magnitude")
        if not notes:
            notes.append("Weak signals")
        
        print(f"{row['ticker']:<8} {row['confidence'].upper():<15} {', '.join(notes)}")
    
    # Statistics
    print("\n" + "="*100)
    print("AGGREGATE STATISTICS:")
    print("-" * 100)
    print(f"Average Direction Accuracy: {df['direction_accuracy'].mean():.4f}")
    print(f"Average Direction F1:       {df['direction_f1'].mean():.4f}")
    print(f"Average Magnitude R²:       {df['magnitude_r2'].mean():.4f}")
    print(f"Average Magnitude MAE:      {df['magnitude_mae'].mean():.3f}%")
    print(f"\nHigh Confidence Count:   {(df['confidence'] == 'high').sum()}/{len(df)}")
    print(f"Medium Confidence Count: {(df['confidence'] == 'medium').sum()}/{len(df)}")
    print(f"Low Confidence Count:    {(df['confidence'] == 'low').sum()}/{len(df)}")
    print("="*100)


if __name__ == "__main__":
    # Configuration
    TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "META", "AMZN"]
    
    end = datetime.today()
    start = end - timedelta(days=365 * 5)
    
    print("="*70)
    print("STOCK PREDICTION MODEL TESTING")
    print("="*70)
    print(f"Date Range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    print(f"Tickers: {', '.join(TICKERS)}")
    print(f"Total Tests: {len(TICKERS)}")
    
    # Run tests
    results = {}
    summaries = []
    
    for ticker in TICKERS:
        try:
            result, summary = test_single_ticker(ticker, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
            if result and summary:
                results[ticker] = result
                summaries.append(summary)
        except Exception as e:
            print(f"\n❌ ERROR testing {ticker}: {e}")
            continue
    
    # Print summary table
    print_summary_table(summaries)
    
    print(f"\n✅ Testing complete. Successfully tested {len(results)}/{len(TICKERS)} tickers.")
    print("Model artifacts saved in 'results' dictionary.")