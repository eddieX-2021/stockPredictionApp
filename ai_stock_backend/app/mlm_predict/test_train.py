"""
Stock Prediction Testing Script

USAGE GUIDE:
------------
To make predictions on new data:

    from app.mlm_predict.train_model import train_stock_models
    
    # Train models
    result = train_stock_models(ticker, start_date, end_date)
    
    # Make prediction
    prediction = result["predict"](X_new)
    
    # Display results
    print(f"Direction: {prediction['direction']}")
    print(f"Confidence: {prediction['direction_confidence']:.2%}")
    print(f"Final Prediction: {prediction['final_prediction_pct']:.2f}%")
    
    # Detailed breakdown:
    print(f"Raw Magnitude: {prediction['raw_magnitude_pct']:.2f}%")
    print(f"With Direction: {prediction['signed_magnitude_pct']:.2f}%")
    print(f"Confidence Score: {prediction['confidence_score']:.2%}")
    print(f"Magnitude Model Used: {prediction['magnitude_model_used']}")  # "UP" or "DOWN"

INTERPRETATION:
---------------
Prediction Fields:
  • direction: UP or DOWN
  • direction_confidence: Probability of UP (0.5-1.0, higher = more confident)
  • raw_magnitude_pct: Predicted move size (always positive, e.g., 1.5%)
  • signed_magnitude_pct: Move with direction applied (e.g., +1.5% or -1.5%)
  • final_prediction_pct: Confidence-scaled prediction (what to show users)
  • confidence_score: How much to trust this prediction (0-1)
  • magnitude_model_used: Which specialist model made the prediction (UP or DOWN)

CONDITIONAL MAGNITUDE MODELING:
-------------------------------
This system uses SEPARATE models for UP and DOWN movements to capture asymmetric volatility:
  • UP Model: Trained only on days that went UP (escalator up - steady climb)
  • DOWN Model: Trained only on days that went DOWN (elevator down - sharp drops)

This captures market reality: stocks fall faster than they rise.

How Confidence Scaling Works:
  • 50% direction confidence (coin flip) → 0% predicted change
  • 75% direction confidence (moderate) → 50% of magnitude
  • 100% direction confidence (certain) → 100% of magnitude

Example:
  Direction: UP (0.85 confidence)
  Raw Magnitude: 2.0% (from UP specialist model)
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
from app.mlm_predict.train_model import train_stock_models


def test_single_ticker(ticker, start_date, end_date):
    """Test a single ticker and return results."""
    print(f"\n{'='*70}")
    print(f"Testing: {ticker}")
    print(f"{'='*70}")
    
    result = train_stock_models(ticker, start_date, end_date, use_cache=False)
    
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
            "magnitude_model_up": mag_info['up']['best_model_name'],
            "magnitude_model_down": mag_info['down']['best_model_name'],
            "magnitude_up_r2": mag_info['up']['metrics']['test']['R²'],
            "magnitude_up_mae": mag_info['up']['metrics']['test']['MAE'],
            "magnitude_down_r2": mag_info['down']['metrics']['test']['R²'],
            "magnitude_down_mae": mag_info['down']['metrics']['test']['MAE'],
            "has_dir_ensemble": dir_info["ensemble"] is not None,
            "has_mag_up_ensemble": mag_info["up"]["ensemble"] is not None,
            "has_mag_down_ensemble": mag_info["down"]["ensemble"] is not None
        }
        
        return result, summary
    
    return None, None


def print_summary_table(summaries):
    """Print a compact summary table of all tested tickers."""
    if not summaries:
        return
    
    df = pd.DataFrame(summaries)
    
    print("\n" + "="*100)
    print("MULTI-TICKER SUMMARY - CONDITIONAL MAGNITUDE MODELING")
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
    
    # UP Magnitude models summary
    print("\nUP MAGNITUDE MODELS (Escalator Up - Steady Climb):")
    print("-" * 100)
    print(f"{'Ticker':<8} {'Model':<20} {'R²':<10} {'MAE':<10} {'Ensemble':<10}")
    print("-" * 100)
    
    for _, row in df.iterrows():
        print(f"{row['ticker']:<8} {row['magnitude_model_up']:<20} "
              f"{row['magnitude_up_r2']:.4f}     {row['magnitude_up_mae']:.3f}%     "
              f"{'Yes' if row['has_mag_up_ensemble'] else 'No':<10}")
    
    # DOWN Magnitude models summary
    print("\nDOWN MAGNITUDE MODELS (Elevator Down - Sharp Drops):")
    print("-" * 100)
    print(f"{'Ticker':<8} {'Model':<20} {'R²':<10} {'MAE':<10} {'Ensemble':<10}")
    print("-" * 100)
    
    for _, row in df.iterrows():
        print(f"{row['ticker']:<8} {row['magnitude_model_down']:<20} "
              f"{row['magnitude_down_r2']:.4f}     {row['magnitude_down_mae']:.3f}%     "
              f"{'Yes' if row['has_mag_down_ensemble'] else 'No':<10}")
    
    # Overall summary
    print("\nOVERALL CONFIDENCE:")
    print("-" * 100)
    print(f"{'Ticker':<8} {'Confidence':<15} {'Notes'}")
    print("-" * 100)
    
    for _, row in df.iterrows():
        notes = []
        if row['direction_accuracy'] > 0.55:
            notes.append("Good direction")
        avg_mag_r2 = (row['magnitude_up_r2'] + row['magnitude_down_r2']) / 2
        if avg_mag_r2 > 0.1:
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
    print(f"\nAverage UP Magnitude R²:    {df['magnitude_up_r2'].mean():.4f}")
    print(f"Average UP Magnitude MAE:   {df['magnitude_up_mae'].mean():.3f}%")
    print(f"\nAverage DOWN Magnitude R²:  {df['magnitude_down_r2'].mean():.4f}")
    print(f"Average DOWN Magnitude MAE: {df['magnitude_down_mae'].mean():.3f}%")
    print(f"\nHigh Confidence Count:   {(df['confidence'] == 'high').sum()}/{len(df)}")
    print(f"Medium Confidence Count: {(df['confidence'] == 'medium').sum()}/{len(df)}")
    print(f"Low Confidence Count:    {(df['confidence'] == 'low').sum()}/{len(df)}")
    
    print("\n" + "="*100)
    print("PREDICTION METHODOLOGY - CONDITIONAL MAGNITUDE:")
    print("-" * 100)
    print("✓ UP Model: Trained ONLY on days that moved UP (captures gradual climbs)")
    print("✓ DOWN Model: Trained ONLY on days that moved DOWN (captures sharp drops)")
    print("✓ Direction model routes prediction to appropriate specialist")
    print("✓ Captures asymmetric volatility: markets fall faster than they rise")
    print("✓ Predictions scaled by confidence: Low confidence → smaller moves")
    print("✓ Final prediction = |magnitude| × direction × confidence_scaling")
    print("="*100)


if __name__ == "__main__":
    # Configuration
    TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "META", "AMZN"]
    
    end = datetime.today()
    start = end - timedelta(days=365 * 6)
    
    print("="*70)
    print("STOCK PREDICTION MODEL TESTING - CONDITIONAL MAGNITUDE")
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