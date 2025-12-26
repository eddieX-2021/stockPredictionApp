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
    
    # Display results
    print(f"Direction: {prediction['direction']}")
    print(f"Confidence: {prediction['direction_confidence']:.2%}")
    print(f"Final Prediction: {prediction['final_prediction_pct']:.2f}%")
    
    # Detailed breakdown:
    print(f"Raw Magnitude: {prediction['raw_magnitude_pct']:.2f}%")
    print(f"With Direction: {prediction['signed_magnitude_pct']:.2f}%")
    print(f"Confidence Score: {prediction['confidence_score']:.2%}")

INTERPRETATION:
---------------
Prediction Fields:
  • direction: UP or DOWN
  • direction_confidence: Probability of UP (0.5-1.0, higher = more confident)
  • raw_magnitude_pct: Predicted move size (always positive, e.g., 1.5%)
  • signed_magnitude_pct: Move with direction applied (e.g., +1.5% or -1.5%)
  • final_prediction_pct: Confidence-scaled prediction (what to show users)
  • confidence_score: How much to trust this prediction (0-1)

How Confidence Scaling Works:
  • 50% direction confidence (coin flip) → 0% predicted change
  • 75% direction confidence (moderate) → 50% of magnitude
  • 100% direction confidence (certain) → 100% of magnitude

Example:
  Direction: UP (0.85 confidence)
  Raw Magnitude: 2.0%
  Confidence Score: 0.70  [calculated as: |0.85 - 0.5| * 2]
  Final Prediction: +1.4%  [calculated as: 2.0% * 0.70]

Overall System Confidence:
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
    Combines them intelligently:
    1. Get direction (UP/DOWN) with confidence
    2. Get magnitude (absolute % change)
    3. Apply direction sign to magnitude
    4. Scale by confidence (lower confidence = smaller predicted move)
    
    Args:
        result: Output from train_stock_models
        X_new: Feature array for prediction (single row or multiple rows)
    
    Returns:
        Dictionary with predictions and confidence
    """
    dir_info = result["direction"]
    mag_info = result["magnitude"]
    
    # Get direction prediction and confidence
    if dir_info["ensemble"]:
        direction_pred, direction_prob = predict_ensemble_direction(X_new, dir_info["ensemble"])
    else:
        X_proc = dir_info["scaler"].transform(X_new) if dir_info["scaler"] else X_new
        direction_pred = dir_info["best_model"].predict(X_proc)
        if hasattr(dir_info["best_model"], "predict_proba"):
            direction_prob = dir_info["best_model"].predict_proba(X_proc)[:, 1]
        else:
            direction_prob = direction_pred
    
    # Get magnitude prediction (absolute value)
    if mag_info["ensemble"]:
        magnitude_pred = predict_ensemble_magnitude(X_new, mag_info["ensemble"])
    else:
        X_proc = mag_info["scaler"].transform(X_new) if mag_info["scaler"] else X_new
        magnitude_pred = mag_info["best_model"].predict(X_proc)
    
    # Ensure magnitude is positive (model should already output positive, but safety check)
    magnitude_pred = np.abs(magnitude_pred)
    
    # Apply direction to magnitude
    # direction_pred: 1 = UP, 0 = DOWN
    # Convert to: 1 = UP (+), -1 = DOWN (-)
    direction_sign = np.where(direction_pred == 1, 1, -1)
    signed_magnitude = magnitude_pred * direction_sign
    
    # Scale magnitude by confidence
    # direction_prob is probability of UP (0 to 1)
    # Convert to confidence: how far from 0.5 (random guess)
    # confidence = 0.5 → multiply by 0 (no confidence, predict 0% change)
    # confidence = 1.0 → multiply by 1 (full confidence, use full magnitude)
    confidence_score = np.abs(direction_prob - 0.5) * 2  # Scale to 0-1
    scaled_magnitude = signed_magnitude * confidence_score
    
    # Handle single vs multiple predictions
    if len(direction_pred) == 1:
        return {
            "direction": "UP" if direction_pred[0] == 1 else "DOWN",
            "direction_confidence": float(direction_prob[0]),
            "raw_magnitude_pct": float(magnitude_pred[0]),  # Absolute value
            "signed_magnitude_pct": float(signed_magnitude[0]),  # With direction applied
            "final_prediction_pct": float(scaled_magnitude[0]),  # Confidence-scaled
            "confidence_score": float(confidence_score[0]),
            "using_ensemble": {
                "direction": dir_info["ensemble"] is not None,
                "magnitude": mag_info["ensemble"] is not None
            }
        }
    else:
        return {
            "direction": ["UP" if d == 1 else "DOWN" for d in direction_pred],
            "direction_confidence": direction_prob.tolist(),
            "raw_magnitude_pct": magnitude_pred.tolist(),
            "signed_magnitude_pct": signed_magnitude.tolist(),
            "final_prediction_pct": scaled_magnitude.tolist(),
            "confidence_score": confidence_score.tolist(),
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
    
    print("\n" + "="*100)
    print("PREDICTION METHODOLOGY:")
    print("-" * 100)
    print("✓ Magnitude models trained on ABSOLUTE values (no directional bias)")
    print("✓ Direction applied separately: UP (+) or DOWN (-)")
    print("✓ Predictions scaled by confidence: Low confidence → smaller moves")
    print("✓ Final prediction = |magnitude| × direction × confidence_scaling")
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