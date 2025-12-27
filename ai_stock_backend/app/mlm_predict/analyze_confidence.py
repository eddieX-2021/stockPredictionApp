"""
Analyze confidence distribution from trained models.
Shows how many predictions fall into high/medium/low confidence buckets.
"""

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from app.mlm_predict.train_model import train_stock_models
from app.mlm_predict.test_train import make_prediction
from app.services.fetch_data import fetch_raw_stock_data, generate_features


def analyze_confidence_distribution(ticker, start_date, end_date):
    """
    Analyze the confidence distribution for a single ticker.
    Returns detailed statistics on prediction confidence levels.
    """
    print(f"\n{'='*70}")
    print(f"Analyzing Confidence Distribution: {ticker}")
    print(f"{'='*70}")
    
    # Train models
    result = train_stock_models(ticker, start_date, end_date)
    
    if not result:
        print(f"Failed to train models for {ticker}")
        return None
    
    # Get test data
    stock_data = fetch_raw_stock_data(ticker, start_date, end_date)
    X, y, stock_data = generate_features(stock_data)
    
    # Use test set (last 20%)
    n = len(X)
    test_start = int(n * 0.8)
    X_test = X.iloc[test_start:]
    
    # Make predictions for all test samples
    predictions = []
    for i in range(len(X_test)):
        X_sample = X_test.iloc[i:i+1]
        pred = make_prediction(result, X_sample)
        predictions.append(pred)
    
    # Extract confidence scores
    dir_confidences = np.array([p['direction_confidence'] for p in predictions])
    conf_scores = np.array([p['confidence_score'] for p in predictions])
    directions = [p['direction'] for p in predictions]
    
    # Categorize by direction confidence
    high_conf_mask = dir_confidences >= 0.65
    medium_conf_mask = (dir_confidences >= 0.55) & (dir_confidences < 0.65)
    low_conf_mask = dir_confidences < 0.55
    
    # Categorize by confidence score (for magnitude scaling)
    high_score_mask = conf_scores >= 0.60
    medium_score_mask = (conf_scores >= 0.30) & (conf_scores < 0.60)
    low_score_mask = conf_scores < 0.30
    
    # Calculate statistics
    total = len(predictions)
    
    stats = {
        'ticker': ticker,
        'total_predictions': total,
        
        # Direction confidence buckets
        'high_dir_conf_count': int(high_conf_mask.sum()),
        'high_dir_conf_pct': float(high_conf_mask.sum() / total * 100),
        'medium_dir_conf_count': int(medium_conf_mask.sum()),
        'medium_dir_conf_pct': float(medium_conf_mask.sum() / total * 100),
        'low_dir_conf_count': int(low_conf_mask.sum()),
        'low_dir_conf_pct': float(low_conf_mask.sum() / total * 100),
        
        # Confidence score buckets (magnitude scaling)
        'high_score_count': int(high_score_mask.sum()),
        'high_score_pct': float(high_score_mask.sum() / total * 100),
        'medium_score_count': int(medium_score_mask.sum()),
        'medium_score_pct': float(medium_score_mask.sum() / total * 100),
        'low_score_count': int(low_score_mask.sum()),
        'low_score_pct': float(low_score_mask.sum() / total * 100),
        
        # Averages
        'avg_dir_confidence': float(dir_confidences.mean()),
        'avg_conf_score': float(conf_scores.mean()),
        'max_dir_confidence': float(dir_confidences.max()),
        'min_dir_confidence': float(dir_confidences.min()),
        
        # Direction distribution in high confidence
        'high_conf_up_count': int(sum(1 for i, d in enumerate(directions) if high_conf_mask[i] and d == 'UP')),
        'high_conf_down_count': int(sum(1 for i, d in enumerate(directions) if high_conf_mask[i] and d == 'DOWN')),
    }
    
    # Print detailed breakdown
    print(f"\nTotal Test Predictions: {total}")
    print(f"\n{'='*70}")
    print("DIRECTION CONFIDENCE DISTRIBUTION")
    print(f"{'='*70}")
    print(f"High (≥65%):   {stats['high_dir_conf_count']:3d} predictions ({stats['high_dir_conf_pct']:.1f}%)")
    print(f"  ↳ UP:   {stats['high_conf_up_count']}")
    print(f"  ↳ DOWN: {stats['high_conf_down_count']}")
    print(f"Medium (55-65%): {stats['medium_dir_conf_count']:3d} predictions ({stats['medium_dir_conf_pct']:.1f}%)")
    print(f"Low (<55%):    {stats['low_dir_conf_count']:3d} predictions ({stats['low_dir_conf_pct']:.1f}%)")
    
    print(f"\n{'='*70}")
    print("CONFIDENCE SCORE DISTRIBUTION (for magnitude scaling)")
    print(f"{'='*70}")
    print(f"High (≥60%):   {stats['high_score_count']:3d} predictions ({stats['high_score_pct']:.1f}%)")
    print(f"Medium (30-60%): {stats['medium_score_count']:3d} predictions ({stats['medium_score_pct']:.1f}%)")
    print(f"Low (<30%):    {stats['low_score_count']:3d} predictions ({stats['low_score_pct']:.1f}%)")
    
    print(f"\n{'='*70}")
    print("SUMMARY STATISTICS")
    print(f"{'='*70}")
    print(f"Average Direction Confidence: {stats['avg_dir_confidence']:.2%}")
    print(f"Average Confidence Score:     {stats['avg_conf_score']:.2%}")
    print(f"Range: {stats['min_dir_confidence']:.2%} - {stats['max_dir_confidence']:.2%}")
    
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
            continue
    
    # Print aggregate summary
    if all_stats:
        print("\n" + "="*70)
        print("AGGREGATE SUMMARY ACROSS ALL TICKERS")
        print("="*70)
        
        df = pd.DataFrame(all_stats)
        
        print("\nDirection Confidence Distribution:")
        print(f"  High (≥65%):   {df['high_dir_conf_pct'].mean():.1f}% of predictions (avg)")
        print(f"  Medium (55-65%): {df['medium_dir_conf_pct'].mean():.1f}% of predictions (avg)")
        print(f"  Low (<55%):    {df['low_dir_conf_pct'].mean():.1f}% of predictions (avg)")
        
        print("\nConfidence Score Distribution:")
        print(f"  High (≥60%):   {df['high_score_pct'].mean():.1f}% of predictions (avg)")
        print(f"  Medium (30-60%): {df['medium_score_pct'].mean():.1f}% of predictions (avg)")
        print(f"  Low (<30%):    {df['low_score_pct'].mean():.1f}% of predictions (avg)")
        
        print("\nAverage Confidences:")
        print(f"  Direction: {df['avg_dir_confidence'].mean():.2%}")
        print(f"  Score:     {df['avg_conf_score'].mean():.2%}")
        
        print("\n" + "="*70)
        print("BY TICKER BREAKDOWN")
        print("="*70)
        print(f"{'Ticker':<8} {'High Dir%':<10} {'High Score%':<12} {'Avg Dir Conf':<15}")
        print("-"*70)
        for _, row in df.iterrows():
            print(f"{row['ticker']:<8} {row['high_dir_conf_pct']:>6.1f}%    "
                  f"{row['high_score_pct']:>6.1f}%       {row['avg_dir_confidence']:>6.2%}")
        
        print("\n" + "="*70)
        print("KEY INSIGHT FOR CONDITIONAL MODELS:")
        print("="*70)
        avg_high_conf = df['high_dir_conf_pct'].mean()
        print(f"\n✓ {avg_high_conf:.1f}% of predictions have ≥65% direction confidence")
        print(f"  → These {avg_high_conf:.1f}% would use conditional (up/down) magnitude models")
        print(f"\n✓ {100-avg_high_conf:.1f}% of predictions have <65% direction confidence")
        print(f"  → These {100-avg_high_conf:.1f}% would use baseline magnitude model (safer)")
        
        if avg_high_conf < 20:
            print("\n⚠️  LOW high-confidence predictions suggests:")
            print("   - Models are uncertain most of the time")
            print("   - Conditional models won't be used often")
            print("   - Focus on improving direction accuracy first")
        elif avg_high_conf < 35:
            print("\n✓ MODERATE high-confidence rate:")
            print("   - Conditional models would be used occasionally")
            print("   - Smart hybrid approach is appropriate")
        else:
            print("\n✓✓ GOOD high-confidence rate:")
            print("   - Conditional models would be used frequently")
            print("   - Smart hybrid approach will provide significant value")


if __name__ == "__main__":
    TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "META", "AMZN"]
    
    print("="*70)
    print("CONFIDENCE DISTRIBUTION ANALYSIS")
    print("="*70)
    print(f"Analyzing: {', '.join(TICKERS)}")
    
    analyze_all_tickers(TICKERS)
    
    print("\n✅ Analysis complete!")