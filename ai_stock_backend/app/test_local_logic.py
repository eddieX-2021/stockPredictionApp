# app/test_local_logic.py
import sys
import os

from matplotlib import ticker

# --- CRITICAL FIX FOR IMPORTS ---
# Get the current directory (app/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (ai_stock_backend/)
parent_dir = os.path.dirname(current_dir)
# Add parent directory to Python path so we can import "app.mlm_predict..."
sys.path.insert(0, parent_dir)

from app.mlm_predict.train_model import train_stock_models

def test_training():
    print("--- STARTING LOGIC TEST ---")
    ticker = "NVDA" 
    
    try:
        print(f"1. Attempting to train/fetch models for {ticker}...")
        # CRITICAL: Using a long date range (5 years) to ensure enough data 
        # for 200-day moving averages and feature generation.
        # use_cache=False forces a fresh training run in RAM without deleting files
        result = train_stock_models(ticker, "2020-01-01", "2025-01-01", verbose=True, use_cache=False)
        
        if not result:
            print("❌ FAILED: Result is None (Check your date range or internet connection)")
            return

        print("2. Validating Result Structure...")
        
        if "magnitude" not in result:
             print("❌ FAILED: Missing 'magnitude' key")
             return
             
        mag_config = result["magnitude"]
        if "conditional" not in mag_config or not mag_config["conditional"]:
            print("❌ FAILED: Model is not marked as conditional")
            return
            
        print("   ✅ Conditional flag found")
        print(f"   ✅ UP Model: {mag_config['up']['best_model_name']}")
        print(f"   ✅ DOWN Model: {mag_config['down']['best_model_name']}")
        
        print("3. Testing Prediction (The Vectorized Code)...")
        latest = result.get("latest_features")
        if latest is None:
            print("❌ FAILED: 'latest_features' was not captured")
            return
            
        pred = result["predict"](latest)
        print("   ✅ Prediction successful!")
        
        # Handle the case where direction is a list (vectorized) vs single value
        d = pred['direction']
        if isinstance(d, list): d = d[0]
        
        m = pred['final_prediction_pct']
        if isinstance(m, list): m = m[0]
            
        print(f"   ➡️ Direction: {d}")
        print(f"   ➡️ Magnitude: {m:.2f}%")
        
        if "magnitude_model_used" in pred:
            used = pred['magnitude_model_used']
            if isinstance(used, list): used = used[0]
            print(f"   ➡️ Specialist Used: {used}")
        else:
             print("❌ WARNING: 'magnitude_model_used' key missing from prediction")

        print("\n🎉 SUCCESS: Core ML Logic is working and crash-free.")

    except Exception as e:
        print(f"\n❌ CRITICAL CRASH: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_training()