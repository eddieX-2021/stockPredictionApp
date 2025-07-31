# yfinance / API integration
import numpy as np
import pandas as pd
import yfinance as yf

def fetch_raw_stock_data(ticker, start_date, end_date):
    try:
        stock_data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
        if stock_data.empty:
            raise ValueError(f"No data retrieved for ticker {ticker} from {start_date} to {end_date}")
        if len(stock_data) < 20:
            raise ValueError(f"Insufficient data: only {len(stock_data)} rows retrieved. Need at least 20 rows for feature calculations.")
        return stock_data
    except Exception as e:
        print(f"Error fetching raw data: {e}")
        return None

def generate_features(stock_data):
    try:
        # Existing features
        stock_data['Lag1'] = stock_data['Close'].shift(1)
        stock_data['Lag2'] = stock_data['Close'].shift(2)
        stock_data['MA5'] = stock_data['Close'].rolling(window=5).mean()
        stock_data['MA10'] = stock_data['Close'].rolling(window=10).mean()
        stock_data['Volume'] = stock_data['Volume']
        stock_data['VMA5'] = stock_data['Volume'].rolling(window=5).mean()
        stock_data['Daily_Return'] = stock_data['Close'].pct_change()
        stock_data['Volatility5'] = stock_data['Daily_Return'].rolling(window=5).std() * np.sqrt(252)
        stock_data['EMA5'] = stock_data['Close'].ewm(span=5, adjust=False).mean()
        stock_data['Price_Change'] = stock_data['Close'].pct_change()
        
        # RSI
        delta = stock_data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        stock_data['RSI14'] = 100 - (100 / (1 + rs))
        
        # New features
        stock_data['Open'] = stock_data['Open']
        stock_data['High'] = stock_data['High']
        stock_data['Low'] = stock_data['Low']
        stock_data['High_Low'] = stock_data['High'] - stock_data['Low']
        stock_data['Close_Open'] = stock_data['Close'] - stock_data['Open']
        stock_data['MA14'] = stock_data['Close'].rolling(window=14).mean()
        stock_data['EMA10'] = stock_data['Close'].ewm(span=10, adjust=False).mean()
        stock_data['EMA14'] = stock_data['Close'].ewm(span=14, adjust=False).mean()
        stock_data['VMA10'] = stock_data['Volume'].rolling(window=10).mean()
        stock_data['OBV'] = (np.sign(stock_data['Close'].diff()) * stock_data['Volume']).cumsum()
        stock_data['MACD'] = stock_data['Close'].ewm(span=12, adjust=False).mean() - stock_data['Close'].ewm(span=26, adjust=False).mean()
        
        # ATR
        stock_data['TR1'] = stock_data['High'] - stock_data['Low']
        stock_data['TR2'] = abs(stock_data['High'] - stock_data['Close'].shift(1))
        stock_data['TR3'] = abs(stock_data['Low'] - stock_data['Close'].shift(1))
        stock_data['TR'] = stock_data[['TR1', 'TR2', 'TR3']].max(axis=1)
        stock_data['ATR'] = stock_data['TR'].rolling(window=14).mean()
        
        stock_data['ROC5'] = stock_data['Close'].pct_change(periods=5)
        
        stock_data = stock_data.drop(['TR1', 'TR2', 'TR3', 'TR'], axis=1)
        
        stock_data['Target'] = stock_data['Close'].shift(-1)
        
        stock_data = stock_data.dropna()
        
        if len(stock_data) < 10:
            raise ValueError(f"Insufficient data after dropping NaNs: only {len(stock_data)} rows remain.")
        
        features = [
            'Close', 'Lag1', 'Lag2', 'MA5', 'MA10', 'Volume', 'VMA5', 'RSI14', 'Volatility5', 'EMA5', 'Price_Change',
            'Open', 'High', 'Low', 'High_Low', 'Close_Open', 'MA14', 'EMA10', 'EMA14', 'VMA10', 'OBV', 'MACD', 'ATR', 'ROC5'
        ]
        X = stock_data[features]
        y = stock_data['Target']
        
        return X, y, stock_data
    except Exception as e:
        print(f"Error generating features: {e}")
        return None, None, None