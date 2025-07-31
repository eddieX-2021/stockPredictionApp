# run_fin.py
import os
import sys

HERE    = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.normpath(os.path.join(HERE, '..', 'src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from predictor import predict_direction

def main():
    ticker = input("🔍 Enter a stock ticker (e.g. AAPL): ").strip().upper()
    if not ticker:
        print("Please enter a ticker symbol!")
        return

    print(f"\n📈 Fetching data and predicting for “{ticker}”…")
    predict_direction(ticker)

if __name__ == '__main__':
    main()
