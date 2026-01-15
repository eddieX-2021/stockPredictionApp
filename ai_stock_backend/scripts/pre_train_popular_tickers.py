"""
Pre-train popular stock tickers to populate cache.
Directly imports the training logic (Serverless) - Perfect for GitHub Actions.

Usage:
    # Run from the root directory (ai_stock_backend)
    python -m scripts.pre_train_popular_tickers
"""

import sys
import os
import time
import random
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# PATH SETUP (Crucial so we can import 'app')
# -----------------------------------------------------------------------------
# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import directly from our app
# CHANGE 1: Added get_model_cache to imports
from app.mlm_predict.train_model import train_stock_models, get_model_cache

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
POPULAR_TICKERS = [
    # Mega Caps
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'AMD',
    
    # Indices
    'SPY', 'QQQ',
    
    # You can uncomment these as your capacity grows
    # 'JPM', 'DIS', 'NFLX', 'COIN'
]

def main():
    print("="*70)
    print("PRE-TRAINING POPULAR STOCK TICKERS (Serverless Mode)")
    print("="*70)
    
    # Date setup (Train on last ~5 years of data)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=1825)).strftime('%Y-%m-%d')
    
    # CHANGE 2: Get the cache instance so we can manually save
    cache = get_model_cache()
    
    successful = []
    failed = []
    
    print(f"Target Date Range: {start_date} to {end_date}")
    print(f"Tickers to process: {len(POPULAR_TICKERS)}\n")

    for i, ticker in enumerate(POPULAR_TICKERS, 1):
        print(f"[{i}/{len(POPULAR_TICKERS)}] Processing {ticker}...", end=" ", flush=True)
        
        start_time = time.time()
        
        try:
            # -------------------------------------------------------
            # DIRECT CALL (No HTTP Request needed)
            # We set use_cache=False to FORCE a retrain/update
            # -------------------------------------------------------
            result = train_stock_models(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                verbose=False,     # Keep logs clean
                use_cache=False    # CRITICAL: Force update!
            )
            
            elapsed = time.time() - start_time
            
            if result:
                # CHANGE 3: Manually save because use_cache=False skips auto-save
                cache.save(ticker, result)
                
                # Print a small summary of what the new model thinks
                direction = result['direction']['best_model_name']
                acc = result['direction']['metrics']['test']['Accuracy']
                print(f"✓ Saved ({elapsed:.1f}s) | Dir Acc: {acc:.2%}")
                successful.append(ticker)
            else:
                print("✗ Failed (No result returned)")
                failed.append(ticker)

        except Exception as e:
            print(f"✗ Error: {e}")
            failed.append(ticker)
            
        # Rate Limiting (Be nice to Yahoo Finance)
        # Sleep 5-10 seconds to look like a human
        sleep_time = random.uniform(5, 8)
        time.sleep(sleep_time)

    # -----------------------------------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------------------------------
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total: {len(POPULAR_TICKERS)}")
    print(f"Success: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed Tickers: {', '.join(failed)}")
        sys.exit(1) # Fail the action if stocks failed
    
    print("\nAll models updated in 'model_cache/'. Ready to commit.")
    sys.exit(0)

if __name__ == "__main__":
    main()