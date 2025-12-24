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
        if len(stock_data) < 50:
            raise ValueError(f"Insufficient data: only {len(stock_data)} rows retrieved. Need at least 50 rows.")
        return stock_data
    except Exception as e:
        print(f"Error fetching raw data: {e}")
        return None


def generate_features(stock_data):
    """
    Generate features optimized for predicting direction and magnitude of price changes.
    Focus on momentum, volatility, and pattern recognition.
    """
    try:
        # ==========================================
        # PRICE MOMENTUM & TRENDS
        # ==========================================
        
        # Short-term momentum (1-5 days)
        stock_data['Return_1d'] = stock_data['Close'].pct_change(1)
        stock_data['Return_2d'] = stock_data['Close'].pct_change(2)
        stock_data['Return_3d'] = stock_data['Close'].pct_change(3)
        stock_data['Return_5d'] = stock_data['Close'].pct_change(5)
        
        # Medium-term momentum (10-20 days)
        stock_data['Return_10d'] = stock_data['Close'].pct_change(10)
        stock_data['Return_20d'] = stock_data['Close'].pct_change(20)
        
        # Moving average crossovers (strong signals for direction)
        stock_data['MA5'] = stock_data['Close'].rolling(5).mean()
        stock_data['MA10'] = stock_data['Close'].rolling(10).mean()
        stock_data['MA20'] = stock_data['Close'].rolling(20).mean()
        stock_data['MA50'] = stock_data['Close'].rolling(50).mean()
        
        stock_data['MA5_MA10_Ratio'] = stock_data['MA5'] / stock_data['MA10']
        stock_data['MA10_MA20_Ratio'] = stock_data['MA10'] / stock_data['MA20']
        stock_data['MA20_MA50_Ratio'] = stock_data['MA20'] / stock_data['MA50']
        stock_data['Price_MA5_Ratio'] = stock_data['Close'] / stock_data['MA5']
        stock_data['Price_MA20_Ratio'] = stock_data['Close'] / stock_data['MA20']
        
        # Exponential moving averages (more responsive to recent changes)
        stock_data['EMA5'] = stock_data['Close'].ewm(span=5, adjust=False).mean()
        stock_data['EMA10'] = stock_data['Close'].ewm(span=10, adjust=False).mean()
        stock_data['EMA20'] = stock_data['Close'].ewm(span=20, adjust=False).mean()
        
        stock_data['EMA5_EMA10_Ratio'] = stock_data['EMA5'] / stock_data['EMA10']
        stock_data['Price_EMA10_Ratio'] = stock_data['Close'] / stock_data['EMA10']
        
        # ==========================================
        # VOLATILITY FEATURES
        # ==========================================
        
        # Historical volatility (annualized)
        stock_data['Volatility_5d'] = stock_data['Return_1d'].rolling(5).std() * np.sqrt(252)
        stock_data['Volatility_10d'] = stock_data['Return_1d'].rolling(10).std() * np.sqrt(252)
        stock_data['Volatility_20d'] = stock_data['Return_1d'].rolling(20).std() * np.sqrt(252)
        
        # Volatility change (increasing vol often precedes big moves)
        stock_data['Vol_Change'] = stock_data['Volatility_10d'] / (stock_data['Volatility_20d'] + 1e-10)
        
        # ==========================================
        # INTRADAY PATTERNS
        # ==========================================
        
        # Price ranges and body size
        stock_data['High_Low_Range'] = (stock_data['High'] - stock_data['Low']) / stock_data['Close']
        stock_data['Body_Size'] = abs(stock_data['Close'] - stock_data['Open']) / stock_data['Close']
        stock_data['Upper_Shadow'] = (stock_data['High'] - stock_data[['Close', 'Open']].max(axis=1)) / stock_data['Close']
        stock_data['Lower_Shadow'] = (stock_data[['Close', 'Open']].min(axis=1) - stock_data['Low']) / stock_data['Close']
        
        # Gap from previous close
        stock_data['Gap'] = (stock_data['Open'] - stock_data['Close'].shift(1)) / stock_data['Close'].shift(1)
        
        # ==========================================
        # VOLUME ANALYSIS
        # ==========================================
        
        # Volume trends
        stock_data['Volume_MA5'] = stock_data['Volume'].rolling(5).mean()
        stock_data['Volume_MA20'] = stock_data['Volume'].rolling(20).mean()
        stock_data['Volume_Ratio'] = stock_data['Volume'] / (stock_data['Volume_MA20'] + 1e-10)
        
        # Volume change
        stock_data['Volume_Change'] = stock_data['Volume'].pct_change()
        
        # Price-Volume relationship
        stock_data['PV_Trend'] = stock_data['Return_1d'] * stock_data['Volume_Ratio']
        
        # On-Balance Volume (OBV) - cumulative volume indicator
        obv = (np.sign(stock_data['Close'].diff()) * stock_data['Volume']).fillna(0).cumsum()
        obv_ma = obv.rolling(20).mean()
        stock_data['OBV_Ratio'] = obv / (obv_ma + 1e-10)
        
        # ==========================================
        # TECHNICAL INDICATORS
        # ==========================================
        
        # RSI (Relative Strength Index)
        delta = stock_data['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        stock_data['RSI'] = 100 - (100 / (1 + rs))
        stock_data['RSI_Normalized'] = (stock_data['RSI'] - 50) / 50  # Center around 0
        
        # Stochastic Oscillator
        low_14 = stock_data['Low'].rolling(14).min()
        high_14 = stock_data['High'].rolling(14).max()
        stock_data['Stochastic'] = 100 * (stock_data['Close'] - low_14) / (high_14 - low_14 + 1e-10)
        
        # MACD (Moving Average Convergence Divergence)
        ema12 = stock_data['Close'].ewm(span=12, adjust=False).mean()
        ema26 = stock_data['Close'].ewm(span=26, adjust=False).mean()
        stock_data['MACD'] = ema12 - ema26
        stock_data['MACD_Signal'] = stock_data['MACD'].ewm(span=9, adjust=False).mean()
        stock_data['MACD_Hist'] = stock_data['MACD'] - stock_data['MACD_Signal']
        stock_data['MACD_Ratio'] = stock_data['MACD'] / stock_data['Close']
        
        # Bollinger Bands
        bb_ma = stock_data['Close'].rolling(20).mean()
        bb_std = stock_data['Close'].rolling(20).std()
        stock_data['BB_Upper'] = bb_ma + (2 * bb_std)
        stock_data['BB_Lower'] = bb_ma - (2 * bb_std)
        stock_data['BB_Width'] = (stock_data['BB_Upper'] - stock_data['BB_Lower']) / bb_ma
        stock_data['BB_Position'] = (stock_data['Close'] - stock_data['BB_Lower']) / (stock_data['BB_Upper'] - stock_data['BB_Lower'] + 1e-10)
        
        # ATR (Average True Range) - volatility measure
        tr1 = stock_data['High'] - stock_data['Low']
        tr2 = abs(stock_data['High'] - stock_data['Close'].shift(1))
        tr3 = abs(stock_data['Low'] - stock_data['Close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        stock_data['ATR'] = tr.rolling(14).mean()
        stock_data['ATR_Pct'] = stock_data['ATR'] / stock_data['Close']
        
        # ==========================================
        # PATTERN RECOGNITION FEATURES
        # ==========================================
        
        # Consecutive up/down days
        stock_data['Consec_Up'] = (stock_data['Close'] > stock_data['Close'].shift(1)).astype(int)
        stock_data['Consec_Up_Count'] = stock_data['Consec_Up'].groupby(
            (stock_data['Consec_Up'] != stock_data['Consec_Up'].shift()).cumsum()
        ).cumsum()
        
        # Price acceleration (change in momentum)
        stock_data['Acceleration'] = stock_data['Return_1d'] - stock_data['Return_1d'].shift(1)
        
        # Distance from highs/lows
        stock_data['High_52w'] = stock_data['High'].rolling(252).max()
        stock_data['Low_52w'] = stock_data['Low'].rolling(252).min()
        stock_data['Dist_From_High'] = (stock_data['High_52w'] - stock_data['Close']) / stock_data['High_52w']
        stock_data['Dist_From_Low'] = (stock_data['Close'] - stock_data['Low_52w']) / stock_data['Close']
        
        # ==========================================
        # TARGET VARIABLE
        # ==========================================
        
        # Next day's closing price
        stock_data['Target'] = stock_data['Close'].shift(-1)
        
        # Clean up intermediate columns
        drop_cols = ['MA5', 'MA10', 'MA20', 'MA50', 'EMA5', 'EMA10', 'EMA20',
                    'Volume_MA5', 'Volume_MA20', 'BB_Upper', 'BB_Lower',
                    'High_52w', 'Low_52w', 'ATR', 'MACD', 'MACD_Signal']
        stock_data = stock_data.drop(columns=drop_cols, errors='ignore')
        
        # Drop NaN rows
        stock_data = stock_data.dropna()
        
        if len(stock_data) < 20:
            raise ValueError(f"Insufficient data after feature generation: {len(stock_data)} rows")
        
        # ==========================================
        # FINAL FEATURE SELECTION
        # ==========================================
        
        features = [
            # Current price (anchor)
            'Close',
            
            # Momentum features
            'Return_1d', 'Return_2d', 'Return_3d', 'Return_5d',
            'Return_10d', 'Return_20d',
            
            # Moving average ratios
            'MA5_MA10_Ratio', 'MA10_MA20_Ratio', 'MA20_MA50_Ratio',
            'Price_MA5_Ratio', 'Price_MA20_Ratio',
            
            # EMA ratios
            'EMA5_EMA10_Ratio', 'Price_EMA10_Ratio',
            
            # Volatility
            'Volatility_5d', 'Volatility_10d', 'Volatility_20d', 'Vol_Change',
            
            # Intraday patterns
            'High_Low_Range', 'Body_Size', 'Upper_Shadow', 'Lower_Shadow', 'Gap',
            
            # Volume
            'Volume_Ratio', 'Volume_Change', 'PV_Trend', 'OBV_Ratio',
            
            # Technical indicators
            'RSI', 'RSI_Normalized', 'Stochastic',
            'MACD_Hist', 'MACD_Ratio',
            'BB_Width', 'BB_Position', 'ATR_Pct',
            
            # Pattern recognition
            'Consec_Up_Count', 'Acceleration',
            'Dist_From_High', 'Dist_From_Low'
        ]
        
        X = stock_data[features]
        y = stock_data['Target']
        
        # Final validation
        if X.isna().any().any():
            print("WARNING: NaN values detected, filling with 0")
            X = X.fillna(0)
        
        if np.isinf(X.values).any():
            print("WARNING: Infinite values detected, replacing with 0")
            X = X.replace([np.inf, -np.inf], 0)
        
        return X, y, stock_data
        
    except Exception as e:
        print(f"Error generating features: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None