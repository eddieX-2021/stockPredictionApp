# yfinance / API integration
import numpy as np
import pandas as pd
import yfinance as yf

def fetch_raw_stock_data(ticker, start_date, end_date):
    try:
        stock_data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
        
        # Flatten MultiIndex columns if present
        if isinstance(stock_data.columns, pd.MultiIndex):
            stock_data.columns = stock_data.columns.get_level_values(0)
        
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
        # ==========================================
        # PRICE-BASED FEATURES (converted to ratios/returns)
        # ==========================================
        
        # Lag features as percentage from current
        stock_data['Lag1_Ratio'] = stock_data['Close'].shift(1) / stock_data['Close']
        stock_data['Lag2_Ratio'] = stock_data['Close'].shift(2) / stock_data['Close']
        
        # Moving averages as ratio to current price
        stock_data['MA5'] = stock_data['Close'].rolling(window=5).mean()
        stock_data['MA10'] = stock_data['Close'].rolling(window=10).mean()
        stock_data['MA14'] = stock_data['Close'].rolling(window=14).mean()
        
        stock_data['MA5_Ratio'] = stock_data['MA5'] / stock_data['Close']
        stock_data['MA10_Ratio'] = stock_data['MA10'] / stock_data['Close']
        stock_data['MA14_Ratio'] = stock_data['MA14'] / stock_data['Close']
        
        # Exponential moving averages as ratio
        stock_data['EMA5'] = stock_data['Close'].ewm(span=5, adjust=False).mean()
        stock_data['EMA10'] = stock_data['Close'].ewm(span=10, adjust=False).mean()
        stock_data['EMA14'] = stock_data['Close'].ewm(span=14, adjust=False).mean()
        
        stock_data['EMA5_Ratio'] = stock_data['EMA5'] / stock_data['Close']
        stock_data['EMA10_Ratio'] = stock_data['EMA10'] / stock_data['Close']
        stock_data['EMA14_Ratio'] = stock_data['EMA14'] / stock_data['Close']
        
        # Daily returns and volatility
        stock_data['Daily_Return'] = stock_data['Close'].pct_change()
        stock_data['Volatility5'] = stock_data['Daily_Return'].rolling(window=5).std() * np.sqrt(252)
        stock_data['Volatility10'] = stock_data['Daily_Return'].rolling(window=10).std() * np.sqrt(252)
        
        # ==========================================
        # INTRADAY PRICE FEATURES (normalized)
        # ==========================================
        
        # Price ranges as percentage of close
        stock_data['High_Low_Pct'] = (stock_data['High'] - stock_data['Low']) / stock_data['Close']
        stock_data['Close_Open_Pct'] = (stock_data['Close'] - stock_data['Open']) / stock_data['Open']
        stock_data['High_Close_Pct'] = (stock_data['High'] - stock_data['Close']) / stock_data['Close']
        stock_data['Close_Low_Pct'] = (stock_data['Close'] - stock_data['Low']) / stock_data['Close']
        
        # ==========================================
        # VOLUME FEATURES (normalized)
        # ==========================================
        
        # Volume relative to its moving average
        stock_data['VMA5'] = stock_data['Volume'].rolling(window=5).mean()
        stock_data['VMA10'] = stock_data['Volume'].rolling(window=10).mean()
        
        stock_data['Volume_Ratio_5'] = stock_data['Volume'] / (stock_data['VMA5'] + 1e-10)
        stock_data['Volume_Ratio_10'] = stock_data['Volume'] / (stock_data['VMA10'] + 1e-10)
        
        # Volume change
        stock_data['Volume_Change'] = stock_data['Volume'].pct_change()
        
        # ==========================================
        # TECHNICAL INDICATORS
        # ==========================================
        
        # RSI (already bounded 0-100)
        delta = stock_data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        stock_data['RSI14'] = 100 - (100 / (1 + rs))
        
        # MACD as ratio to price (normalize it)
        macd = stock_data['Close'].ewm(span=12, adjust=False).mean() - stock_data['Close'].ewm(span=26, adjust=False).mean()
        stock_data['MACD_Ratio'] = macd / stock_data['Close']
        
        # ATR as percentage of close
        stock_data['TR1'] = stock_data['High'] - stock_data['Low']
        stock_data['TR2'] = abs(stock_data['High'] - stock_data['Close'].shift(1))
        stock_data['TR3'] = abs(stock_data['Low'] - stock_data['Close'].shift(1))
        stock_data['TR'] = stock_data[['TR1', 'TR2', 'TR3']].max(axis=1)
        stock_data['ATR'] = stock_data['TR'].rolling(window=14).mean()
        stock_data['ATR_Pct'] = stock_data['ATR'] / stock_data['Close']
        
        # Rate of Change (already a percentage)
        stock_data['ROC5'] = stock_data['Close'].pct_change(periods=5)
        stock_data['ROC10'] = stock_data['Close'].pct_change(periods=10)
        
        # OBV - normalized by dividing by rolling mean to prevent unbounded growth
        obv_raw = (np.sign(stock_data['Close'].diff()) * stock_data['Volume']).cumsum()
        obv_ma = obv_raw.rolling(window=20).mean()
        stock_data['OBV_Ratio'] = obv_raw / (obv_ma + 1e-10)
        
        # ==========================================
        # MOMENTUM FEATURES
        # ==========================================
        
        stock_data['Momentum_3'] = stock_data['Close'].pct_change(periods=3)
        stock_data['Momentum_7'] = stock_data['Close'].pct_change(periods=7)
        
        # ==========================================
        # TARGET VARIABLE (next day's price)
        # ==========================================
        
        # Predict next day's actual closing price
        stock_data['Target'] = stock_data['Close'].shift(-1)
        
        # Clean up temporary columns
        stock_data = stock_data.drop([
            'TR1', 'TR2', 'TR3', 'TR', 'MA5', 'MA10', 'MA14', 
            'EMA5', 'EMA10', 'EMA14', 'VMA5', 'VMA10', 'ATR'
        ], axis=1)
        
        # Drop NaN rows
        stock_data = stock_data.dropna()
        
        if len(stock_data) < 10:
            raise ValueError(f"Insufficient data after dropping NaNs: only {len(stock_data)} rows remain.")
        
        # ==========================================
        # SELECT FINAL FEATURES (all normalized/ratio-based)
        # ==========================================
        
        features = [
            # CRITICAL: Current price as anchor for predicting next day's price
            'Close',
            
            # Lag ratios
            'Lag1_Ratio', 'Lag2_Ratio',
            
            # MA ratios
            'MA5_Ratio', 'MA10_Ratio', 'MA14_Ratio',
            
            # EMA ratios
            'EMA5_Ratio', 'EMA10_Ratio', 'EMA14_Ratio',
            
            # Returns and volatility
            'Daily_Return', 'Volatility5', 'Volatility10',
            
            # Intraday patterns
            'High_Low_Pct', 'Close_Open_Pct', 'High_Close_Pct', 'Close_Low_Pct',
            
            # Volume
            'Volume_Ratio_5', 'Volume_Ratio_10', 'Volume_Change',
            
            # Technical indicators
            'RSI14', 'MACD_Ratio', 'ATR_Pct', 'OBV_Ratio',
            
            # Momentum
            'ROC5', 'ROC10', 'Momentum_3', 'Momentum_7'
        ]
        
        X = stock_data[features]
        y = stock_data['Target']
        
        # Final validation - check for any remaining issues
        if X.isna().any().any():
            print("WARNING: NaN values detected in features")
            X = X.fillna(0)
        
        if np.isinf(X.values).any():
            print("WARNING: Infinite values detected in features")
            X = X.replace([np.inf, -np.inf], 0)
        
        return X, y, stock_data
        
    except Exception as e:
        print(f"Error generating features: {e}")
        return None, None, None