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


def fetch_market_context(start_date, end_date):
    """
    Fetch only the most critical market indicators.
    Limited to 3 sources to avoid overfitting and multicollinearity.
    """
    try:
        # S&P 500 (market benchmark) - ESSENTIAL
        spy = yf.download("SPY", start=start_date, end=end_date, progress=False, auto_adjust=True)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)
        
        # VIX (fear gauge) - ESSENTIAL for volatility context
        vix = yf.download("^VIX", start=start_date, end=end_date, progress=False, auto_adjust=True)
        if isinstance(vix.columns, pd.MultiIndex):
            vix.columns = vix.columns.get_level_values(0)
        
        return {
            'SPY': spy,
            'VIX': vix
        }
    except Exception as e:
        print(f"Warning: Could not fetch market context: {e}")
        return None


def generate_features(stock_data):
    """
    Generate BIAS-NEUTRAL features optimized for predicting direction and magnitude.
    Features focus on magnitude, deviation from normal, and relative positioning rather than raw directional values.
    """
    try:
        # Get date range from stock data
        start_date = stock_data.index[0]
        end_date = stock_data.index[-1]
        
        # Fetch market context data
        market_data = fetch_market_context(start_date, end_date)
        
        # ==========================================
        # RAW RETURNS (for calculating derived features)
        # ==========================================
        
        returns_1d = stock_data['Close'].pct_change(1)
        returns_2d = stock_data['Close'].pct_change(2)
        returns_3d = stock_data['Close'].pct_change(3)
        returns_5d = stock_data['Close'].pct_change(5)
        returns_10d = stock_data['Close'].pct_change(10)
        returns_20d = stock_data['Close'].pct_change(20)
        
        # ==========================================
        # MARKET CONTEXT FEATURES (BIAS-NEUTRAL)
        # ==========================================
        
        if market_data:
            # SPY returns (raw)
            spy = market_data['SPY']
            spy_returns = spy['Close'].pct_change().reindex(stock_data.index, method='ffill')
            
            # BIAS-NEUTRAL: Z-scored market return (how unusual is today's market move?)
            spy_mean = spy_returns.rolling(20).mean()
            spy_std = spy_returns.rolling(20).std()
            stock_data['SPY_Return_Zscore'] = (spy_returns - spy_mean) / (spy_std + 1e-10)
            
            # BIAS-NEUTRAL: Absolute market return (magnitude only)
            stock_data['SPY_Return_Abs'] = abs(spy_returns)
            
            # BIAS-NEUTRAL: Relative strength as absolute difference
            rel_strength = returns_1d - spy_returns
            stock_data['Relative_Strength_Abs'] = abs(rel_strength)
            
            # VIX (fear index) - already neutral (high = volatile)
            vix = market_data['VIX']
            stock_data['VIX'] = vix['Close'].reindex(stock_data.index, method='ffill')
            
            # Market stress indicator (VIX spike = danger)
            stock_data['Market_Stress'] = (stock_data['VIX'] > 25).astype(float)
            
            # VIX change (increasing volatility = uncertainty)
            vix_values = stock_data['VIX']
            stock_data['VIX_Change'] = vix_values.pct_change()
        
        # ==========================================
        # BIAS-NEUTRAL MOMENTUM FEATURES
        # ==========================================
        
        # Z-scored returns (how unusual is this move relative to recent history?)
        for period, returns in [('1d', returns_1d), ('5d', returns_5d), ('10d', returns_10d)]:
            mean = returns.rolling(20).mean()
            std = returns.rolling(20).std()
            stock_data[f'Return_{period}_Zscore'] = (returns - mean) / (std + 1e-10)
        
        # Absolute returns (magnitude only, no direction)
        stock_data['Return_1d_Abs'] = abs(returns_1d)
        stock_data['Return_5d_Abs'] = abs(returns_5d)
        stock_data['Return_10d_Abs'] = abs(returns_10d)
        
        # Volatility of returns (how choppy is the price action?)
        stock_data['Return_Volatility_5d'] = returns_1d.rolling(5).std()
        stock_data['Return_Volatility_20d'] = returns_1d.rolling(20).std()
        
        # ==========================================
        # MOVING AVERAGES (NEUTRAL POSITIONING)
        # ==========================================
        
        ma5 = stock_data['Close'].rolling(5).mean()
        ma10 = stock_data['Close'].rolling(10).mean()
        ma20 = stock_data['Close'].rolling(20).mean()
        ma50 = stock_data['Close'].rolling(50).mean()
        
        # Distance from MAs (can be positive or negative - neutral)
        stock_data['Price_MA5_Dist'] = (stock_data['Close'] - ma5) / ma5
        stock_data['Price_MA20_Dist'] = (stock_data['Close'] - ma20) / ma20
        stock_data['Price_MA50_Dist'] = (stock_data['Close'] - ma50) / ma50
        
        # Absolute distance from MAs (magnitude only)
        stock_data['Price_MA20_Dist_Abs'] = abs((stock_data['Close'] - ma20) / ma20)
        
        # MA spreads (trend strength, not direction)
        stock_data['MA5_MA10_Spread'] = abs(ma5 - ma10) / ma10
        stock_data['MA10_MA20_Spread'] = abs(ma10 - ma20) / ma20
        stock_data['MA20_MA50_Spread'] = abs(ma20 - ma50) / ma50
        
        # EMAs
        ema5 = stock_data['Close'].ewm(span=5, adjust=False).mean()
        ema10 = stock_data['Close'].ewm(span=10, adjust=False).mean()
        ema20 = stock_data['Close'].ewm(span=20, adjust=False).mean()
        
        # EMA distances (neutral)
        stock_data['Price_EMA10_Dist'] = (stock_data['Close'] - ema10) / ema10
        stock_data['EMA5_EMA10_Spread'] = abs(ema5 - ema10) / ema10
        
        # ==========================================
        # VOLATILITY FEATURES (INHERENTLY NEUTRAL)
        # ==========================================
        
        # Historical volatility (annualized)
        stock_data['Volatility_5d'] = returns_1d.rolling(5).std() * np.sqrt(252)
        stock_data['Volatility_10d'] = returns_1d.rolling(10).std() * np.sqrt(252)
        stock_data['Volatility_20d'] = returns_1d.rolling(20).std() * np.sqrt(252)
        
        # Volatility change (increasing vol often precedes big moves)
        stock_data['Vol_Change'] = stock_data['Volatility_10d'] / (stock_data['Volatility_20d'] + 1e-10)
        
        # Volatility regime (high vs low)
        stock_data['High_Vol_Regime'] = (stock_data['Volatility_20d'] > stock_data['Volatility_20d'].rolling(60).mean()).astype(float)
        
        # ==========================================
        # INTRADAY PATTERNS (NEUTRAL)
        # ==========================================
        
        # Price ranges and body size
        stock_data['High_Low_Range'] = (stock_data['High'] - stock_data['Low']) / stock_data['Close']
        stock_data['Body_Size'] = abs(stock_data['Close'] - stock_data['Open']) / stock_data['Close']
        stock_data['Upper_Shadow'] = (stock_data['High'] - stock_data[['Close', 'Open']].max(axis=1)) / stock_data['Close']
        stock_data['Lower_Shadow'] = (stock_data[['Close', 'Open']].min(axis=1) - stock_data['Low']) / stock_data['Close']
        
        # Gap from previous close (can be + or -, neutral)
        stock_data['Gap'] = (stock_data['Open'] - stock_data['Close'].shift(1)) / stock_data['Close'].shift(1)
        stock_data['Gap_Abs'] = abs(stock_data['Gap'])
        
        # ==========================================
        # VOLUME ANALYSIS (NEUTRAL)
        # ==========================================
        
        # Volume trends
        volume_ma5 = stock_data['Volume'].rolling(5).mean()
        volume_ma20 = stock_data['Volume'].rolling(20).mean()
        stock_data['Volume_Ratio'] = stock_data['Volume'] / (volume_ma20 + 1e-10)
        
        # Volume change (can be + or -, neutral)
        stock_data['Volume_Change'] = stock_data['Volume'].pct_change()
        
        # Price-Volume divergence (absolute value - looking for unusual patterns)
        stock_data['PV_Divergence'] = abs(returns_1d) * stock_data['Volume_Ratio']
        
        # On-Balance Volume (OBV) - cumulative volume indicator
        obv = (np.sign(stock_data['Close'].diff()) * stock_data['Volume']).fillna(0).cumsum()
        obv_ma = obv.rolling(20).mean()
        stock_data['OBV_Ratio'] = obv / (obv_ma + 1e-10)
        
        # Volume surge detection (spike in volume = potential move)
        stock_data['Volume_Surge'] = (stock_data['Volume_Ratio'] > 1.5).astype(float)
        
        # ==========================================
        # TECHNICAL INDICATORS (NORMALIZED/NEUTRAL)
        # ==========================================
        
        # RSI (already 0-100, but we normalize around 50)
        delta = stock_data['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        stock_data['RSI'] = 100 - (100 / (1 + rs))
        stock_data['RSI_Normalized'] = (stock_data['RSI'] - 50) / 50  # -1 to 1, centered at 0
        
        # RSI extremes (overbought/oversold - mean reversion signals)
        stock_data['RSI_Extreme'] = ((stock_data['RSI'] > 70) | (stock_data['RSI'] < 30)).astype(float)
        
        # Stochastic Oscillator (normalized)
        low_14 = stock_data['Low'].rolling(14).min()
        high_14 = stock_data['High'].rolling(14).max()
        stoch = 100 * (stock_data['Close'] - low_14) / (high_14 - low_14 + 1e-10)
        stock_data['Stochastic'] = stoch
        stock_data['Stochastic_Normalized'] = (stoch - 50) / 50
        
        # MACD (use histogram only - momentum measure)
        ema12 = stock_data['Close'].ewm(span=12, adjust=False).mean()
        ema26 = stock_data['Close'].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        stock_data['MACD_Hist'] = macd - macd_signal
        stock_data['MACD_Hist_Normalized'] = stock_data['MACD_Hist'] / stock_data['Close']
        
        # MACD momentum (change in MACD histogram)
        stock_data['MACD_Momentum'] = stock_data['MACD_Hist'].diff()
        
        # Bollinger Bands (position within bands is neutral)
        bb_ma = stock_data['Close'].rolling(20).mean()
        bb_std = stock_data['Close'].rolling(20).std()
        bb_upper = bb_ma + (2 * bb_std)
        bb_lower = bb_ma - (2 * bb_std)
        stock_data['BB_Width'] = (bb_upper - bb_lower) / bb_ma
        stock_data['BB_Position'] = (stock_data['Close'] - bb_lower) / (bb_upper - bb_lower + 1e-10)
        
        # BB extremes (touching bands = potential reversal)
        stock_data['BB_Extreme'] = ((stock_data['BB_Position'] > 0.95) | (stock_data['BB_Position'] < 0.05)).astype(float)
        
        # ATR (Average True Range) - volatility measure (neutral)
        tr1 = stock_data['High'] - stock_data['Low']
        tr2 = abs(stock_data['High'] - stock_data['Close'].shift(1))
        tr3 = abs(stock_data['Low'] - stock_data['Close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        stock_data['ATR'] = tr.rolling(14).mean()
        stock_data['ATR_Pct'] = stock_data['ATR'] / stock_data['Close']
        
        # ==========================================
        # PATTERN RECOGNITION (NEUTRAL)
        # ==========================================
        
        # Consecutive up/down days - USE ABSOLUTE COUNT (momentum persistence)
        consec_up = (stock_data['Close'] > stock_data['Close'].shift(1)).astype(int)
        consec_count = consec_up.groupby(
            (consec_up != consec_up.shift()).cumsum()
        ).cumsum()
        stock_data['Consec_Days'] = consec_count  # Can be interpreted as streak length
        
        # Momentum acceleration (2nd derivative - change in momentum)
        stock_data['Acceleration'] = returns_1d.diff()
        stock_data['Acceleration_Abs'] = abs(stock_data['Acceleration'])
        
        # Distance from 52-week highs/lows (mean reversion signals)
        high_52w = stock_data['High'].rolling(252).max()
        low_52w = stock_data['Low'].rolling(252).min()
        stock_data['Dist_From_High'] = (high_52w - stock_data['Close']) / high_52w
        stock_data['Dist_From_Low'] = (stock_data['Close'] - low_52w) / stock_data['Close']
        
        # Near extremes (close to 52w high or low)
        stock_data['Near_52w_Extreme'] = ((stock_data['Dist_From_High'] < 0.05) | (stock_data['Dist_From_Low'] < 0.05)).astype(float)
        
        # ==========================================
        # TARGET VARIABLE
        # ==========================================
        
        # Next day's closing price
        stock_data['Target'] = stock_data['Close'].shift(-1)
        
        # Drop NaN rows
        stock_data = stock_data.dropna()
        
        if len(stock_data) < 20:
            raise ValueError(f"Insufficient data after feature generation: {len(stock_data)} rows")
        
        # ==========================================
        # FINAL FEATURE SELECTION (BIAS-NEUTRAL)
        # ==========================================
        
        features = [
            # MARKET CONTEXT (NEUTRAL)
            'SPY_Return_Zscore',      # How unusual is market move (can be + or -)
            'SPY_Return_Abs',         # Market move magnitude
            'Relative_Strength_Abs',  # Magnitude of outperformance
            'VIX',                    # Volatility level
            'Market_Stress',          # High volatility regime
            'VIX_Change',             # Increasing/decreasing fear
            
            # MOMENTUM (NEUTRAL - z-scored and absolute)
            'Return_1d_Zscore', 'Return_5d_Zscore', 'Return_10d_Zscore',
            'Return_1d_Abs', 'Return_5d_Abs', 'Return_10d_Abs',
            'Return_Volatility_5d', 'Return_Volatility_20d',
            
            # MOVING AVERAGES (NEUTRAL - distances can be + or -)
            'Price_MA5_Dist', 'Price_MA20_Dist', 'Price_MA50_Dist',
            'Price_MA20_Dist_Abs',
            'MA5_MA10_Spread', 'MA10_MA20_Spread', 'MA20_MA50_Spread',
            'Price_EMA10_Dist', 'EMA5_EMA10_Spread',
            
            # VOLATILITY (NEUTRAL)
            'Volatility_5d', 'Volatility_10d', 'Volatility_20d', 'Vol_Change',
            'High_Vol_Regime',
            
            # INTRADAY PATTERNS (NEUTRAL)
            'High_Low_Range', 'Body_Size', 'Upper_Shadow', 'Lower_Shadow',
            'Gap', 'Gap_Abs',
            
            # VOLUME (NEUTRAL)
            'Volume_Ratio', 'Volume_Change', 'PV_Divergence', 'OBV_Ratio',
            'Volume_Surge',
            
            # TECHNICAL INDICATORS (NORMALIZED/NEUTRAL)
            'RSI_Normalized', 'RSI_Extreme',
            'Stochastic_Normalized',
            'MACD_Hist_Normalized', 'MACD_Momentum',
            'BB_Width', 'BB_Position', 'BB_Extreme',
            'ATR_Pct',
            
            # PATTERN RECOGNITION (NEUTRAL)
            'Consec_Days', 'Acceleration', 'Acceleration_Abs',
            'Dist_From_High', 'Dist_From_Low', 'Near_52w_Extreme'
        ]
        
        # Filter out features that don't exist (in case market data fetch failed)
        features = [f for f in features if f in stock_data.columns]
        
        X = stock_data[features]
        y = stock_data['Target']
        
        # Final validation
        if X.isna().any().any():
            print("WARNING: NaN values detected, filling with 0")
            X = X.fillna(0)
        
        if np.isinf(X.values).any():
            print("WARNING: Infinite values detected, replacing with 0")
            X = X.replace([np.inf, -np.inf], 0)
        
        market_feature_count = 6 if market_data else 0
        print(f"✓ Generated {len(features)} BIAS-NEUTRAL features (including {market_feature_count} market context features)")
        
        return X, y, stock_data
        
    except Exception as e:
        print(f"Error generating features: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None