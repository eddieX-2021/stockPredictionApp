from datetime import datetime, timedelta
from app.mlm_predict.train_model import train_stock_models

if __name__ == "__main__":
    ticker = "AAPL"
    end = datetime.today()
    start = end - timedelta(days=365 * 5)

    model, scaler = train_stock_models(
        ticker,
        start.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d")
    )

    print("Training finished.")