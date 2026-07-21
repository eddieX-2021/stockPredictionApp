import sys
from app.reddit.pipeline.export_dataset import export_weak_labeled_dataset

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.scripts.reddit_export_dataset TSLA")
        raise SystemExit(2)

    ticker = sys.argv[1].strip().upper()
    out = export_weak_labeled_dataset(ticker)
    print({"dataset_path": out})
