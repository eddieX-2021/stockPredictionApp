"""
Pre-train popular stock tickers to populate cache
Run this script weekly (or whenever you want to refresh popular tickers)

Usage:
    python scripts/pre_train_popular_tickers.py
    
Or with custom API URL:
    python scripts/pre_train_popular_tickers.py --api-url http://localhost:8000
"""

import requests
import time
import argparse
from datetime import datetime


# Popular tickers to pre-train
POPULAR_TICKERS = [
    # Mega Caps (Tech Giants)
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
    
    # Major Indices ETFs
    'SPY', 'VOO',
    
    # Popular Tech Stocks
    'AMD', 'INTC', 'NFLX', 
    
    # 'ADBE', 'CRM', 'ORCL', 'NBIS', 'RDDT',

    # # Space
    # 'ASTS', 'RKLB', 'LUNR',

    # # Database
    # 'PLTR', 'MU',
    
    # # Finance
    # 'JPM', 'BAC', 'GS', 'V', 'MA',
    
    # # Consumer
    # 'DIS', 'NKE', 'SBUX', 'MCD', 'KO', 'PEP',
    
    # # Healthcare
    # 'UNH', 'JNJ', 'PFE', 'ABBV',
    
    # # Energy
    # 'XOM', 'CVX',
    
    # # Industrial/Aerospace
    # 'BA', 'CAT',
    
    # # Communication
    # 'T', 'VZ',
    
    # # Crypto-related
    # 'COIN', 'MSTR'
]


def pre_train_tickers(api_url: str, tickers: list):
    """
    Pre-train models for a list of tickers
    
    Args:
        api_url: Base URL of the API (e.g., http://localhost:8000)
        tickers: List of ticker symbols to pre-train
    """
    print("="*70)
    print("PRE-TRAINING POPULAR STOCK TICKERS")
    print("="*70)
    print(f"API URL: {api_url}")
    print(f"Tickers to train: {len(tickers)}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    print()
    
    successful = []
    failed = []
    skipped = []
    
    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] Training {ticker}...", end=" ")
        
        try:
            start_time = time.time()
            
            # Make prediction request (will train if not cached)
            response = requests.get(
                f"{api_url}/predict",
                params={"stock": ticker},
                timeout=600  # 2 minute timeout per ticker
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                was_cached = data.get("model_info", {}).get("cached", False)
                
                if was_cached:
                    print(f"✓ Already cached ({elapsed:.1f}s)")
                    skipped.append(ticker)
                else:
                    print(f"✓ Trained successfully ({elapsed:.1f}s)")
                    successful.append(ticker)
                    
                # Show prediction info
                print(f"    → Prediction: {data['direction']} {data['predicted_change_pct']:+.2f}% "
                      f"(confidence: {data['confidence']:.2%})")
            else:
                print(f"✗ Failed (HTTP {response.status_code})")
                failed.append((ticker, f"HTTP {response.status_code}"))
                
        except requests.exceptions.Timeout:
            print(f"✗ Timeout (>120s)")
            failed.append((ticker, "Timeout"))
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            failed.append((ticker, str(e)))
        
        # Small delay between requests to avoid overwhelming the server
        if i < len(tickers):
            time.sleep(1)
    
    # Summary
    print()
    print("="*70)
    print("PRE-TRAINING SUMMARY")
    print("="*70)
    print(f"Total tickers: {len(tickers)}")
    print(f"Successfully trained: {len(successful)}")
    print(f"Already cached: {len(skipped)}")
    print(f"Failed: {len(failed)}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    if successful:
        print(f"\n✓ Trained: {', '.join(successful)}")
    
    if skipped:
        print(f"\n⊙ Skipped (already cached): {', '.join(skipped)}")
    
    if failed:
        print(f"\n✗ Failed:")
        for ticker, reason in failed:
            print(f"  - {ticker}: {reason}")
    
    print()
    
    # Return stats for programmatic use
    return {
        'successful': successful,
        'skipped': skipped,
        'failed': failed,
        'total': len(tickers)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Pre-train popular stock tickers for model caching"
    )
    parser.add_argument(
        '--api-url',
        type=str,
        default='http://localhost:8000',
        help='Base URL of the API (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--tickers',
        type=str,
        nargs='+',
        help='Custom list of tickers to train (overrides default popular list)'
    )
    
    args = parser.parse_args()
    
    # Use custom tickers if provided, otherwise use default popular list
    tickers = args.tickers if args.tickers else POPULAR_TICKERS
    
    # Run pre-training
    results = pre_train_tickers(args.api_url, tickers)
    
    # Exit with error code if any failed
    if results['failed']:
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    main()