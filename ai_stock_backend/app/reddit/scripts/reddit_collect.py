import sys
from app.reddit.pipeline.collect import collect_for_ticker

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.scripts.reddit_collect TSLA")
        raise SystemExit(2)

    ticker = sys.argv[1].strip().upper()
    result = collect_for_ticker(ticker)
    print(result)
