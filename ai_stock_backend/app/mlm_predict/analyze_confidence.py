"""
Enhanced confidence analyzer with accuracy tracking and bias detection.
Shows prediction distribution, accuracy by confidence level, and directional bias.
"""

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from app.mlm_predict.train_model import train_stock_models


def analyze_confidence_distribution(ticker, start_date, end_date):
    """
    Analyze confidence distribution and accuracy for a single ticker.
    Includes actual vs predicted direction comparison and bias detection.
    """
    print(f"\n{'='*70}")
    print(f"Analyzing Confidence Distribution: {ticker}")
    print(f"{'='*70}")
    
    # Train models with test data returned
    result = train_stock_models(ticker, start_date, end_date, return_data=True)
    
    if not result:
        print(f"Failed to train models for {ticker}")
        return None
    
    # Get test data
    test_data = result["test_data"]
    X_test = test_data["X_test"]
    y_actual = test_data["y_direction_test"]
    
    # Feature importance analysis
    print(f"\n{'='*70}")
    print("FEATURE IMPORTANCE ANALYSIS")
    print(f"{'='*70}")
    
    dir_model = result['direction']['best_model']
    feature_names = X_test.columns
    
    if hasattr(dir_model, 'feature_importances_'):
        importances = dir_model.feature_importances_
        
        # Sort by importance
        indices = np.argsort(importances)[::-1][:15]  # Top 15 features
        
        print(f"\nTop 15 Most Important Features for {result['direction']['best_model_name']}:")
        print("-"*70)
        for i, idx in enumerate(indices, 1):
            print(f"{i:2d}. {feature_names[idx]:30s} {importances[idx]:.4f}")
    elif hasattr(dir_model, 'coef_'):
        # For linear models like Logistic Regression
        coefs = np.abs(dir_model.coef_[0])
        indices = np.argsort(coefs)[::-1][:15]
        
        print(f"\nTop 15 Most Important Features for {result['direction']['best_model_name']}:")
        print("-"*70)
        for i, idx in enumerate(indices, 1):
            print(f"{i:2d}. {feature_names[idx]:30s} {coefs[idx]:.4f}")
    else:
        print(f"\n{result['direction']['best_model_name']} does not support feature importance.")
    
    # Make predictions for all test samples
    predictions = []
    for i in range(len(X_test)):
        X_sample = X_test.iloc[i:i+1]
        pred = result["predict"](X_sample)
        predictions.append(pred)
    
    # Extract data
    dir_confidences = np.array([p['direction_confidence'] for p in predictions])
    conf_scores = np.array([p['confidence_score'] for p in predictions])
    pred_directions = np.array([1 if p['direction'] == 'UP' else 0 for p in predictions])
    
    # Calculate accuracy
    correct = (pred_directions == y_actual).astype(int)
    overall_accuracy = correct.mean()
    
    # Define confidence thresholds (symmetric)
    HIGH_UP_THRESHOLD = 0.70
    HIGH_DOWN_THRESHOLD = 0.30
    MEDIUM_UP_THRESHOLD = 0.60
    MEDIUM_DOWN_THRESHOLD = 0.40

    # Categorize predictions
    high_conf_mask = (dir_confidences >= HIGH_UP_THRESHOLD) | (dir_confidences <= HIGH_DOWN_THRESHOLD)
    medium_conf_mask = ((dir_confidences >= MEDIUM_UP_THRESHOLD) & (dir_confidences < HIGH_UP_THRESHOLD)) | \
                       ((dir_confidences > HIGH_DOWN_THRESHOLD) & (dir_confidences <= MEDIUM_DOWN_THRESHOLD))
    low_conf_mask = (dir_confidences > MEDIUM_DOWN_THRESHOLD) & (dir_confidences < MEDIUM_UP_THRESHOLD)

    # Separate UP and DOWN high confidence
    high_conf_up = ((pred_directions == 1) & (dir_confidences >= HIGH_UP_THRESHOLD)).sum()
    high_conf_down = ((pred_directions == 0) & (dir_confidences <= HIGH_DOWN_THRESHOLD)).sum()
    
    # Calculate accuracy by confidence level
    high_conf_correct = correct[high_conf_mask].sum() if high_conf_mask.sum() > 0 else 0
    high_conf_total = high_conf_mask.sum()
    high_conf_accuracy = high_conf_correct / high_conf_total if high_conf_total > 0 else 0
    
    medium_conf_correct = correct[medium_conf_mask].sum() if medium_conf_mask.sum() > 0 else 0
    medium_conf_total = medium_conf_mask.sum()
    medium_conf_accuracy = medium_conf_correct / medium_conf_total if medium_conf_total > 0 else 0
    
    low_conf_correct = correct[low_conf_mask].sum() if low_conf_mask.sum() > 0 else 0
    low_conf_total = low_conf_mask.sum()
    low_conf_accuracy = low_conf_correct / low_conf_total if low_conf_total > 0 else 0
    
    # Direction distribution analysis
    total = len(predictions)
    total_up = (pred_directions == 1).sum()
    total_down = (pred_directions == 0).sum()
    
    # High confidence breakdown
    high_conf_up_count = ((pred_directions == 1) & high_conf_mask).sum()
    high_conf_down_count = ((pred_directions == 0) & high_conf_mask).sum()
    
    # Actual market direction distribution (for comparison)
    actual_up = (y_actual == 1).sum()
    actual_down = (y_actual == 0).sum()
    
    # Bias detection: compare prediction distribution to actual distribution
    pred_up_pct = total_up / total * 100
    actual_up_pct = actual_up / total * 100
    bias = pred_up_pct - actual_up_pct
    
    stats = {
        'ticker': ticker,
        'total_predictions': total,
        
        # Overall prediction distribution
        'total_up_predictions': int(total_up),
        'total_up_pct': float(pred_up_pct),
        'total_down_predictions': int(total_down),
        'total_down_pct': float(total_down / total * 100),
        
        # Actual market distribution
        'actual_up': int(actual_up),
        'actual_up_pct': float(actual_up_pct),
        'actual_down': int(actual_down),
        'actual_down_pct': float(actual_down / total * 100),
        
        # Bias metric
        'up_bias': float(bias),
        
        # Confidence levels
        'high_conf_count': int(high_conf_total),
        'high_conf_pct': float(high_conf_total / total * 100),
        'high_conf_up': int(high_conf_up_count),
        'high_conf_down': int(high_conf_down_count),
        'high_conf_accuracy': float(high_conf_accuracy),
        'high_conf_correct': int(high_conf_correct),
        
        'medium_conf_count': int(medium_conf_total),
        'medium_conf_pct': float(medium_conf_total / total * 100),
        'medium_conf_accuracy': float(medium_conf_accuracy),
        'medium_conf_correct': int(medium_conf_correct),
        
        'low_conf_count': int(low_conf_total),
        'low_conf_pct': float(low_conf_total / total * 100),
        'low_conf_accuracy': float(low_conf_accuracy),
        'low_conf_correct': int(low_conf_correct),
        
        # Overall accuracy
        'overall_accuracy': float(overall_accuracy),
        'overall_correct': int(correct.sum()),
        
        # Averages
        'avg_dir_confidence': float(dir_confidences.mean()),
        'avg_conf_score': float(conf_scores.mean()),
    }
    
    # Print detailed breakdown
    print(f"\nTotal Test Predictions: {total}")
    print(f"Overall Accuracy: {stats['overall_accuracy']:.2%} ({stats['overall_correct']}/{total} correct)")
    
    print(f"\n{'='*70}")
    print("PREDICTION vs ACTUAL DISTRIBUTION")
    print(f"{'='*70}")
    print(f"Predicted UP:   {stats['total_up_predictions']:3d} ({stats['total_up_pct']:.1f}%)")
    print(f"Predicted DOWN: {stats['total_down_predictions']:3d} ({stats['total_down_pct']:.1f}%)")
    print(f"\nActual UP:      {stats['actual_up']:3d} ({stats['actual_up_pct']:.1f}%)")
    print(f"Actual DOWN:    {stats['actual_down']:3d} ({stats['actual_down_pct']:.1f}%)")
    print(f"\nUP Bias: {stats['up_bias']:+.1f}%", end="")
    if abs(bias) > 10:
        print(" ⚠️  SIGNIFICANT BIAS DETECTED")
    elif abs(bias) > 5:
        print(" ⚠️  Moderate bias")
    else:
        print(" ✓ Minimal bias")
    
    print(f"\n{'='*70}")
    print("ACCURACY BY CONFIDENCE LEVEL")
    print(f"{'='*70}")
    print(f"High (≥70% or ≤30%): {stats['high_conf_count']:3d} predictions ({stats['high_conf_pct']:.1f}%)")
    print(f"  ↳ Accuracy: {stats['high_conf_accuracy']:.2%} ({stats['high_conf_correct']}/{stats['high_conf_count']} correct)")
    print(f"  ↳ UP: {stats['high_conf_up']}, DOWN: {stats['high_conf_down']}")
    
    print(f"\nMedium (60-70% or 30-40%): {stats['medium_conf_count']:3d} predictions ({stats['medium_conf_pct']:.1f}%)")
    print(f"  ↳ Accuracy: {stats['medium_conf_accuracy']:.2%} ({stats['medium_conf_correct']}/{stats['medium_conf_count']} correct)")
    
    print(f"\nLow (40-60%):    {stats['low_conf_count']:3d} predictions ({stats['low_conf_pct']:.1f}%)")
    print(f"  ↳ Accuracy: {stats['low_conf_accuracy']:.2%} ({stats['low_conf_correct']}/{stats['low_conf_count']} correct)")
    
    print(f"\n{'='*70}")
    print("CONFIDENCE QUALITY CHECK")
    print(f"{'='*70}")
    if stats['high_conf_accuracy'] > stats['medium_conf_accuracy'] > stats['low_conf_accuracy']:
        print("✓✓ GOOD: Confidence correlates with accuracy")
    elif stats['high_conf_accuracy'] > stats['overall_accuracy']:
        print("✓ OK: High confidence is better than average")
    else:
        print("⚠️  WARNING: Confidence may not be reliable")
    
    return stats


def analyze_all_tickers(tickers):
    """Analyze confidence distribution across multiple tickers."""
    end = datetime.today()
    start = end - timedelta(days=365 * 5)
    
    all_stats = []
    
    for ticker in tickers:
        try:
            stats = analyze_confidence_distribution(
                ticker,
                start.strftime("%Y-%m-%d"),
                end.strftime("%Y-%m-%d")
            )
            if stats:
                all_stats.append(stats)
        except Exception as e:
            print(f"\n❌ ERROR analyzing {ticker}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Print aggregate summary
    if all_stats:
        print("\n" + "="*70)
        print("AGGREGATE SUMMARY ACROSS ALL TICKERS")
        print("="*70)
        
        df = pd.DataFrame(all_stats)
        
        print("\nOverall Performance:")
        print(f"  Average Accuracy: {df['overall_accuracy'].mean():.2%}")
        print(f"  High Conf Accuracy: {df['high_conf_accuracy'].mean():.2%}")
        print(f"  Medium Conf Accuracy: {df['medium_conf_accuracy'].mean():.2%}")
        print(f"  Low Conf Accuracy: {df['low_conf_accuracy'].mean():.2%}")
        
        print("\nPrediction Distribution:")
        print(f"  Predicted UP: {df['total_up_pct'].mean():.1f}% (avg)")
        print(f"  Actual UP: {df['actual_up_pct'].mean():.1f}% (avg)")
        print(f"  Average UP Bias: {df['up_bias'].mean():+.1f}%")
        
        print("\nHigh Confidence Analysis:")
        print(f"  Average % of predictions: {df['high_conf_pct'].mean():.1f}%")
        print(f"  Average accuracy: {df['high_conf_accuracy'].mean():.2%}")
        
        # Calculate high confidence bias
        avg_high_conf_up_pct = (df['high_conf_up'] / df['high_conf_count']).mean() * 100
        print(f"  High conf UP predictions: {avg_high_conf_up_pct:.1f}% (avg)")
        
        if avg_high_conf_up_pct > 70:
            print("  ⚠️  HIGH CONFIDENCE PREDICTIONS ARE HEAVILY SKEWED UP")
        elif avg_high_conf_up_pct > 60:
            print("  ⚠️  High confidence predictions lean UP")
        elif avg_high_conf_up_pct < 40:
            print("  ⚠️  High confidence predictions lean DOWN")
        else:
            print("  ✓ High confidence predictions are balanced")
        
        print("\n" + "="*70)
        print("DETAILED BREAKDOWN BY TICKER")
        print("="*70)
        print(f"{'Ticker':<8} {'Overall Acc':<12} {'High Acc':<10} {'High%':<8} {'UP Bias':<10}")
        print("-"*70)
        for _, row in df.iterrows():
            print(f"{row['ticker']:<8} {row['overall_accuracy']:>6.2%}       "
                  f"{row['high_conf_accuracy']:>6.2%}     "
                  f"{row['high_conf_pct']:>5.1f}%   "
                  f"{row['up_bias']:>+6.1f}%")
        
        print("\n" + "="*70)
        print("BIAS ANALYSIS")
        print("="*70)
        
        significant_bias = df[abs(df['up_bias']) > 10]
        if len(significant_bias) > 0:
            print(f"\n⚠️  {len(significant_bias)}/{len(df)} tickers show SIGNIFICANT bias (>10%):")
            for _, row in significant_bias.iterrows():
                print(f"  {row['ticker']}: {row['up_bias']:+.1f}% bias")
        else:
            print("\n✓ No tickers show significant bias")
        
        print("\n" + "="*70)
        print("RECOMMENDATIONS")
        print("="*70)
        
        avg_bias = df['up_bias'].mean()
        if abs(avg_bias) > 10:
            print("\n⚠️  SYSTEMATIC UP BIAS DETECTED")
            print("Possible causes:")
            print("  1. Training period was mostly bullish (2020-2025)")
            print("  2. Features favor UP predictions")
            print("  3. Class imbalance in training data")
            print("\nSuggestions:")
            print("  - Add class weights to balance UP/DOWN (already implemented)")
            print("  - Train on longer period including bear markets")
            print("  - Check if SPY_Return or market features are biased")
            print("  - Consider removing time-dependent features")
        elif avg_bias > 5:
            print("\n⚠️  Moderate UP bias present")
            print("  - Monitor feature importance for bias sources")
            print("  - Consider additional class balancing techniques")
        else:
            print("\n✓ Bias is within acceptable range")
        
        avg_high_acc = df['high_conf_accuracy'].mean()
        avg_overall_acc = df['overall_accuracy'].mean()
        
        if avg_high_acc > avg_overall_acc + 0.05:
            print("\n✓ Confidence calibration is working well")
        else:
            print("\n⚠️  Confidence may not be well-calibrated")
            print("  - High confidence predictions should be more accurate")
            print("  - Consider adjusting confidence thresholds")


if __name__ == "__main__":
    TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "META", "AMZN"]
    
    print("="*70)
    print("ENHANCED CONFIDENCE DISTRIBUTION ANALYSIS")
    print("="*70)
    print(f"Analyzing: {', '.join(TICKERS)}")
    
    analyze_all_tickers(TICKERS)
    
    print("\n✅ Analysis complete!")