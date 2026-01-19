"""
Model Caching System for Stock Prediction
Saves trained model results to disk to avoid retraining
"""

import os
import pickle
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any


class ModelCache:
    """Handles caching and loading of trained model results"""
    
    def __init__(self, cache_dir: str = "model_cache", cache_duration_days: int = 7):
        """
        Initialize model cache
        """
        # Ensure we find the root directory correctly regardless of where this is run
        current_file = os.path.abspath(__file__)
        app_dir = os.path.dirname(os.path.dirname(current_file)) # app/
        backend_dir = os.path.dirname(app_dir) # ai_stock_backend/
        
        self.cache_dir = Path(backend_dir) / cache_dir
        
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_duration = timedelta(days=cache_duration_days)
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self._load_metadata()
    
    def _load_metadata(self):
        """Load cache metadata from disk"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    self.metadata = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load cache metadata: {e}")
                self.metadata = {}
        else:
            self.metadata = {}
    
    def _save_metadata(self):
        """Save cache metadata to disk"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache metadata: {e}")
    
    def _get_cache_path(self, ticker: str) -> Path:
        """Get file path for cached model result"""
        return self.cache_dir / f"{ticker.upper()}_model.pkl"
    
    def get(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached model result if valid
        """
        ticker = ticker.upper()
        cache_path = self._get_cache_path(ticker)
        
        # Check if cache exists in metadata
        if ticker not in self.metadata:
            return None
        
        cache_info = self.metadata[ticker]
        
        # Check if expired (based on TTL)
        cached_time = datetime.fromisoformat(cache_info['timestamp'])
        age = datetime.now() - cached_time
        
        if age > self.cache_duration:
            print(f"[CACHE] Model for {ticker} expired ({age.days} days old, TTL: {self.cache_duration.days} days)")
            self._invalidate(ticker)
            return None
        
        # Check if file exists
        if not cache_path.exists():
            print(f"[CACHE] Cache file missing for {ticker}")
            self._invalidate(ticker)
            return None
        
        # Load model result
        try:
            print(f"[CACHE] ✓ Loading cached model for {ticker} (trained {age.days} days ago)")
            with open(cache_path, 'rb') as f:
                result = pickle.load(f)
            
            # Re-add the predict function (wasn't cached because it can't be pickled)
            # Use dynamic import to avoid circular dependency
            from app.mlm_predict.train_model import make_prediction
            result["predict"] = lambda X_new: make_prediction(result, X_new)
            
            return result
        except Exception as e:
            print(f"[CACHE] Error loading cached model for {ticker}: {e}")
            self._invalidate(ticker)
            return None
    
    def save(self, ticker: str, result: Dict[str, Any]):
        """
        Save trained model result to cache
        """
        ticker = ticker.upper()
        cache_path = self._get_cache_path(ticker)
        
        try:
            # Create a copy without the predict function (can't pickle local functions)
            result_to_cache = result.copy()
            if 'predict' in result_to_cache:
                del result_to_cache['predict']
            
            # Save the model result
            with open(cache_path, 'wb') as f:
                pickle.dump(result_to_cache, f)
            
            # --- CRITICAL FIX: Handle Conditional Model Structure ---
            # Old way: result['magnitude']['best_model_name'] (This key is gone now!)
            # New way: Check if it's conditional, then log accordingly
            
            mag_model_name = "Unknown"
            mag_data = result.get('magnitude', {})
            
            if mag_data.get('conditional'):
                # It's our new conditional model
                up_name = mag_data.get('up', {}).get('best_model_name', '?')
                down_name = mag_data.get('down', {}).get('best_model_name', '?')
                mag_model_name = f"Cond: {up_name}/{down_name}"
            elif 'best_model_name' in mag_data:
                # It's the old single model
                mag_model_name = mag_data['best_model_name']
                
            # Update metadata
            self.metadata[ticker] = {
                'timestamp': datetime.now().isoformat(),
                'confidence': result.get('confidence', 'unknown'),
                'direction_model': result['direction']['best_model_name'],
                'magnitude_model': mag_model_name
            }
            self._save_metadata()
            
            print(f"[CACHE] ✓ Model cached for {ticker}")
        except Exception as e:
            print(f"[CACHE] Error saving model to cache: {e}")
            import traceback
            traceback.print_exc()
    
    def _invalidate(self, ticker: str):
        """Remove cache entry for a ticker"""
        ticker = ticker.upper()
        
        # Remove from metadata
        if ticker in self.metadata:
            del self.metadata[ticker]
            self._save_metadata()
        
        # Remove file
        cache_path = self._get_cache_path(ticker)
        if cache_path.exists():
            try:
                cache_path.unlink()
            except Exception as e:
                print(f"Warning: Could not delete cache file for {ticker}: {e}")
    
    def clear_expired(self):
        """Remove all expired cache entries"""
        expired_tickers = []
        
        for ticker, cache_info in self.metadata.items():
            cached_time = datetime.fromisoformat(cache_info['timestamp'])
            if datetime.now() - cached_time > self.cache_duration:
                expired_tickers.append(ticker)
        
        for ticker in expired_tickers:
            print(f"[CACHE] Removing expired cache for {ticker}")
            self._invalidate(ticker)
        
        if expired_tickers:
            print(f"[CACHE] Cleared {len(expired_tickers)} expired entries")
        else:
            print("[CACHE] No expired entries to clear")
    
    def clear_ticker(self, ticker: str):
        """Clear cache for a specific ticker"""
        ticker = ticker.upper()
        self._invalidate(ticker)
        print(f"[CACHE] Cleared cache for {ticker}")
    
    def clear_all(self):
        """Clear entire cache"""
        for ticker in list(self.metadata.keys()):
            self._invalidate(ticker)
        print("[CACHE] All cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_models = len(self.metadata)
        expired = 0
        active = 0
        
        for ticker, cache_info in self.metadata.items():
            cached_time = datetime.fromisoformat(cache_info['timestamp'])
            if datetime.now() - cached_time > self.cache_duration:
                expired += 1
            else:
                active += 1
        
        # Calculate total cache size
        total_size = 0
        for ticker in self.metadata.keys():
            cache_path = self._get_cache_path(ticker)
            if cache_path.exists():
                total_size += cache_path.stat().st_size
        
        total_size_mb = total_size / (1024 * 1024)
        
        # Get list of cached tickers with details
        cached_tickers = []
        for ticker, cache_info in self.metadata.items():
            cached_time = datetime.fromisoformat(cache_info['timestamp'])
            age_days = (datetime.now() - cached_time).days
            cached_tickers.append({
                'ticker': ticker,
                'age_days': age_days,
                'confidence': cache_info.get('confidence', 'unknown'),
                'is_expired': age_days > self.cache_duration.days
            })
        
        return {
            'total_models': total_models,
            'active_models': active,
            'expired_models': expired,
            'total_size_mb': round(total_size_mb, 2),
            'cache_duration_days': self.cache_duration.days,
            'cached_tickers': sorted(cached_tickers, key=lambda x: x['age_days'])
        }
    
    def list_cached_tickers(self) -> list:
        """Get list of all cached tickers"""
        return sorted(list(self.metadata.keys()))