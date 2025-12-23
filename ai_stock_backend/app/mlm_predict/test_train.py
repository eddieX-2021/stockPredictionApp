from datetime import datetime, timedelta
from app.mlm_predict.train_model import train_stock_models

if __name__ == "__main__":
    ticker = "AAPL"
    end = datetime.today()
    start = end - timedelta(days=365 * 5)

    tickers = ["AAPL", "TSLA", "GME", "JPM", "XOM", "NVDA"]
    for ticker in tickers:
        print(f"\n{'='*60}\nTesting {ticker}\n{'='*60}")
        result = train_stock_models(ticker, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    if result:
        model = result["best_model"]
        scaler = result["scaler"]
        model_name = result["best_model_name"]
        metrics = result["metrics"]
        
        print("\nTraining finished.")
        print(f"Best model: {model_name}")
        print(f"Test R²: {metrics['test']['R²']:.4f}")
        print(f"Test NRMSE: {metrics['test']['NRMSE (%)']:.2f}%")
        
        # You can access the full model report if needed
        # print("\nAll model results:")
        # for name, stats in result["model_report"].items():
        #     print(f"{name}: Val R² = {stats['validation']['R²']:.4f}")
    else:
        print("Training failed.")