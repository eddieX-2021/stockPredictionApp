import numpy as np
import pandas as pd
# CHANGED: Added HistGradientBoosting, removed others to clean up imports
from sklearn.ensemble import (RandomForestClassifier, RandomForestRegressor,
                              GradientBoostingClassifier, GradientBoostingRegressor,
                              AdaBoostClassifier, AdaBoostRegressor,
                              HistGradientBoostingClassifier, HistGradientBoostingRegressor)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             r2_score, mean_squared_error, mean_absolute_error,
                             classification_report, confusion_matrix)
from sklearn.neural_network import MLPClassifier, MLPRegressor
from xgboost import XGBClassifier, XGBRegressor
from catboost import CatBoostClassifier, CatBoostRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from joblib import Parallel, delayed
import os
from app.services.fetch_data import fetch_raw_stock_data, generate_features
from app.mlm_predict.model_cache import ModelCache

# Optional: LightGBM
try:
    from lightgbm import LGBMClassifier, LGBMRegressor
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

# Models that benefit from scaling
MODELS_NEEDING_SCALING = {"Logistic Regression", "Ridge", "MLP"}

# Initialize global model cache (survives across function calls)
_model_cache = ModelCache(cache_dir="model_cache", cache_duration_days=7)


def predict_ensemble_direction(X, ensemble_info):
    """Predict direction using weighted voting ensemble."""
    if ensemble_info is None:
        raise ValueError("No ensemble information provided")
    
    models = ensemble_info["models"]
    weights = ensemble_info["weights"]
    scalers = ensemble_info["scalers"]
    model_names = ensemble_info["model_names"]
    
    weighted_probs = np.zeros(len(X))
    
    for i, (model, scaler, name) in enumerate(zip(models, scalers, model_names)):
        X_proc = scaler.transform(X) if scaler is not None else X
        
        if hasattr(model, "predict_proba"):
            prob = model.predict_proba(X_proc)[:, 1]
        else:
            prob = model.predict(X_proc)
        
        weighted_probs += prob * weights[i]
    
    predictions = (weighted_probs >= 0.5).astype(int)
    return predictions, weighted_probs


def predict_ensemble_magnitude(X, ensemble_info):
    """Predict magnitude using weighted average ensemble."""
    if ensemble_info is None:
        raise ValueError("No ensemble information provided")
    
    models = ensemble_info["models"]
    weights = ensemble_info["weights"]
    scalers = ensemble_info["scalers"]
    model_names = ensemble_info["model_names"]
    
    predictions = []
    
    for i, (model, scaler, name) in enumerate(zip(models, scalers, model_names)):
        X_proc = scaler.transform(X) if scaler is not None else X
        pred = model.predict(X_proc)
        predictions.append(pred * weights[i])
    
    return sum(predictions)


def make_prediction(result, X_new):
    """
    Make a complete prediction using both direction and conditional magnitude models.
    
    CONDITIONAL MAGNITUDE: Uses separate UP and DOWN models for asymmetric volatility.
    
    Combines direction and magnitude intelligently:
    1. Get direction (UP/DOWN) with confidence
    2. Route to appropriate magnitude model (UP or DOWN specialist)
    3. Apply direction sign to magnitude
    4. Scale by confidence (lower confidence = smaller predicted move)
    
    Args:
        result: Output from train_stock_models
        X_new: Feature array for prediction (single row or multiple rows)
    
    Returns:
        Dictionary with predictions and confidence metrics
    """
    dir_info = result["direction"]
    mag_info = result["magnitude"]
    
    # Ensure X_new is 2D
    if len(X_new.shape) == 1:
        X_new = X_new.reshape(1, -1)
    
    # Get direction prediction and confidence
    if dir_info["ensemble"]:
        direction_pred, direction_prob = predict_ensemble_direction(X_new, dir_info["ensemble"])
    else:
        X_proc = dir_info["scaler"].transform(X_new) if dir_info["scaler"] else X_new
        direction_pred = dir_info["best_model"].predict(X_proc)
        if hasattr(dir_info["best_model"], "predict_proba"):
            direction_prob = dir_info["best_model"].predict_proba(X_proc)[:, 1]
        else:
            direction_prob = direction_pred
    
    # CONDITIONAL MAGNITUDE PREDICTION (VECTORIZED)
    # Split predictions by direction and route to appropriate specialist model
    up_mask = (direction_pred == 1)
    down_mask = (direction_pred == 0)
    
    magnitude_pred = np.zeros(len(direction_pred))
    
    # Process UP predictions
    if up_mask.any():
        X_up = X_new[up_mask]
        
        if mag_info["up"]["ensemble"]:
            magnitude_pred[up_mask] = predict_ensemble_magnitude(X_up, mag_info["up"]["ensemble"])
        else:
            X_up_proc = mag_info["up"]["scaler"].transform(X_up) if mag_info["up"]["scaler"] else X_up
            magnitude_pred[up_mask] = mag_info["up"]["best_model"].predict(X_up_proc)
    
    # Process DOWN predictions
    if down_mask.any():
        X_down = X_new[down_mask]
        
        if mag_info["down"]["ensemble"]:
            magnitude_pred[down_mask] = predict_ensemble_magnitude(X_down, mag_info["down"]["ensemble"])
        else:
            X_down_proc = mag_info["down"]["scaler"].transform(X_down) if mag_info["down"]["scaler"] else X_down
            magnitude_pred[down_mask] = mag_info["down"]["best_model"].predict(X_down_proc)
    
    # Ensure magnitude is positive
    magnitude_pred = np.abs(magnitude_pred)
    
    # Apply direction to magnitude
    # direction_pred: 1 = UP, 0 = DOWN
    # Convert to: 1 = UP (+), -1 = DOWN (-)
    direction_sign = np.where(direction_pred == 1, 1, -1)
    signed_magnitude = magnitude_pred * direction_sign
    
    # Scale magnitude by confidence
    # direction_prob is probability of UP (0 to 1)
    # Convert to confidence: how far from 0.5 (random guess)
    confidence_score = np.abs(direction_prob - 0.5) * 2  # Scale to 0-1
    scaled_magnitude = signed_magnitude * confidence_score
    
    # Handle single vs multiple predictions
    if len(direction_pred) == 1:
        return {
            "direction": "UP" if direction_pred[0] == 1 else "DOWN",
            "direction_confidence": float(direction_prob[0]),
            "raw_magnitude_pct": float(magnitude_pred[0]),
            "signed_magnitude_pct": float(signed_magnitude[0]),
            "final_prediction_pct": float(scaled_magnitude[0]),
            "confidence_score": float(confidence_score[0]),
            "using_ensemble": {
                "direction": dir_info["ensemble"] is not None,
                "magnitude_up": mag_info["up"]["ensemble"] is not None,
                "magnitude_down": mag_info["down"]["ensemble"] is not None
            },
            "magnitude_model_used": "UP" if direction_pred[0] == 1 else "DOWN"
        }
    else:
        return {
            "direction": ["UP" if d == 1 else "DOWN" for d in direction_pred],
            "direction_confidence": direction_prob.tolist(),
            "raw_magnitude_pct": magnitude_pred.tolist(),
            "signed_magnitude_pct": signed_magnitude.tolist(),
            "final_prediction_pct": scaled_magnitude.tolist(),
            "confidence_score": confidence_score.tolist(),
            "using_ensemble": {
                "direction": dir_info["ensemble"] is not None,
                "magnitude_up": mag_info["up"]["ensemble"] is not None,
                "magnitude_down": mag_info["down"]["ensemble"] is not None
            },
            "magnitude_model_used": ["UP" if d == 1 else "DOWN" for d in direction_pred]
        }


def train_direction_model(name, model, X_train, y_train, X_val, y_val, X_test, y_test, scaler=None):
    """Train and evaluate a classification model for direction prediction."""
    try:
        if name in MODELS_NEEDING_SCALING and scaler is not None:
            X_train_proc = scaler.fit_transform(X_train)
            X_val_proc = scaler.transform(X_val)
            X_test_proc = scaler.transform(X_test)
        else:
            X_train_proc = X_train
            X_val_proc = X_val
            X_test_proc = X_test
        
        model.fit(X_train_proc, y_train)
        
        # Validation metrics
        y_val_pred = model.predict(X_val_proc)
        val_accuracy = accuracy_score(y_val, y_val_pred)
        val_precision = precision_score(y_val, y_val_pred, zero_division=0)
        val_recall = recall_score(y_val, y_val_pred, zero_division=0)
        val_f1 = f1_score(y_val, y_val_pred, zero_division=0)
        
        # Test metrics
        y_test_pred = model.predict(X_test_proc)
        test_accuracy = accuracy_score(y_test, y_test_pred)
        test_precision = precision_score(y_test, y_test_pred, zero_division=0)
        test_recall = recall_score(y_test, y_test_pred, zero_division=0)
        test_f1 = f1_score(y_test, y_test_pred, zero_division=0)
        
        return name, model, {
            "validation": {
                "Accuracy": val_accuracy,
                "Precision": val_precision,
                "Recall": val_recall,
                "F1": val_f1
            },
            "test": {
                "Accuracy": test_accuracy,
                "Precision": test_precision,
                "Recall": test_recall,
                "F1": test_f1
            }
        }, scaler if name in MODELS_NEEDING_SCALING else None
        
    except Exception as e:
        print(f"Error training {name}: {e}")
        return name, None, None, None


def train_magnitude_model(name, model, X_train, y_train, X_val, y_val, X_test, y_test, scaler=None):
    """Train and evaluate a regression model for magnitude prediction."""
    try:
        if name in MODELS_NEEDING_SCALING and scaler is not None:
            X_train_proc = scaler.fit_transform(X_train)
            X_val_proc = scaler.transform(X_val)
            X_test_proc = scaler.transform(X_test)
        else:
            X_train_proc = X_train
            X_val_proc = X_val
            X_test_proc = X_test
        
        model.fit(X_train_proc, y_train)
        
        # Validation metrics
        y_val_pred = model.predict(X_val_proc)
        val_r2 = r2_score(y_val, y_val_pred)
        val_mae = mean_absolute_error(y_val, y_val_pred)
        val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
        
        # Test metrics
        y_test_pred = model.predict(X_test_proc)
        test_r2 = r2_score(y_test, y_test_pred)
        test_mae = mean_absolute_error(y_test, y_test_pred)
        test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
        
        return name, model, {
            "validation": {
                "R²": val_r2,
                "MAE": val_mae,
                "RMSE": val_rmse
            },
            "test": {
                "R²": test_r2,
                "MAE": test_mae,
                "RMSE": test_rmse
            }
        }, scaler if name in MODELS_NEEDING_SCALING else None
        
    except Exception as e:
        print(f"Error training {name}: {e}")
        return name, None, None, None


def train_stock_models(ticker, start_date, end_date, verbose=True, return_data=False, use_cache=True):
    """
    Train dual prediction system with CONDITIONAL MAGNITUDE models.
    """
    ticker = ticker.upper()
    
    # Try to load from cache first if enabled
    if use_cache:
        cached_result = _model_cache.get(ticker)
        if cached_result is not None:
            # --- SELF-HEALING CHECK ---
            # Check if this cache file is compatible with our new code
            # It MUST have 'magnitude' -> 'up' structure
            is_compatible = False
            try:
                if "magnitude" in cached_result and "up" in cached_result["magnitude"]:
                    is_compatible = True
            except Exception:
                pass

            if is_compatible:
                if verbose:
                    print(f"[CACHE] ✓ Using cached model for {ticker}")
                
                # Re-add the predict function
                cached_result["predict"] = lambda X_new: make_prediction(cached_result, X_new)
                cached_result["cached"] = True
                return cached_result
            else:
                if verbose:
                    print(f"[CACHE] ⚠ Found cache for {ticker} but it is incompatible (Old Version). Retraining...")
    
    # No cache or cache disabled - train new models
    if verbose:
        print(f"[TRAINING] Training new models for {ticker}...")
    
    stock_data = fetch_raw_stock_data(ticker, start_date, end_date)
    if stock_data is None:
        if verbose:
            print("Failed to fetch data.")
        return None

    # DON'T cut the data yet - we need the full history for feature calculation
    # Feature generation needs lookback for rolling windows (MA50, 252-day high, etc.)
    if verbose:
        print(f"Fetched {len(stock_data)} rows of raw data")

    # Generate features with full historical data for proper rolling window calculations
    result = generate_features(stock_data, return_latest_for_prediction=True)

    if len(result) == 4:
        # We got the prediction row separated
        X, y_price, stock_data, latest_features = result
        if verbose:
            print(f"✓ Latest features captured for prediction (shape: {latest_features.shape})")
    else:
        # Fallback (shouldn't happen with current data)
        X, y_price, stock_data = result
        latest_features = None
        if verbose:
            print("⚠ No prediction row available (data might be stale)")

    if X is None or y_price is None:
        if verbose:
            print("Failed to generate features.")
        return None

    # NOW cut to last 1250 rows for training (features are already calculated correctly)
    if len(X) > 1250:
        X = X.tail(1250)
        y_price = y_price.tail(1250)
        stock_data = stock_data.tail(1250)
        if verbose:
            print(f"✓ Trimmed to last 1250 rows for training efficiency")
    
    # Align the data
    current_prices = stock_data['Close'].values
    
    # Create direction target (1 = up, 0 = down)
    y_direction = (y_price.values > current_prices).astype(int)
    
    # Create magnitude target (ABSOLUTE percentage change)
    pct_change = ((y_price.values - current_prices) / current_prices) * 100
    y_magnitude = np.abs(pct_change)

    # Sequential split (60% train, 20% val, 20% test)
    n = len(X)
    train_end = int(n * 0.6)
    val_end = int(n * 0.8)
    
    X_train = X[:train_end]
    X_val = X[train_end:val_end]
    X_test = X[val_end:]
    
    y_dir_train = y_direction[:train_end]
    y_dir_val = y_direction[train_end:val_end]
    y_dir_test = y_direction[val_end:]
    
    y_mag_train = y_magnitude[:train_end]
    y_mag_val = y_magnitude[train_end:val_end]
    y_mag_test = y_magnitude[val_end:]

    # =========================================================================
    # CONDITIONAL MAGNITUDE SPLIT: Separate UP and DOWN movements
    # =========================================================================
    
    # Training set split
    mask_up_train = (y_dir_train == 1)
    mask_down_train = (y_dir_train == 0)
    
    X_train_up = X_train[mask_up_train]
    y_mag_train_up = y_mag_train[mask_up_train]
    
    X_train_down = X_train[mask_down_train]
    y_mag_train_down = y_mag_train[mask_down_train]
    
    # Validation set split
    mask_up_val = (y_dir_val == 1)
    mask_down_val = (y_dir_val == 0)
    
    X_val_up = X_val[mask_up_val]
    y_mag_val_up = y_mag_val[mask_up_val]
    
    X_val_down = X_val[mask_down_val]
    y_mag_val_down = y_mag_val[mask_down_val]
    
    # Test set split
    mask_up_test = (y_dir_test == 1)
    mask_down_test = (y_dir_test == 0)
    
    X_test_up = X_test[mask_up_test]
    y_mag_test_up = y_mag_test[mask_up_test]
    
    X_test_down = X_test[mask_down_test]
    y_mag_test_down = y_mag_test[mask_down_test]

    if verbose:
        print(f"\n{'='*60}")
        print("DATA SPLIT SUMMARY")
        print("="*60)
        print(f"Training set: {len(X_train)} samples")
        print(f"  └─ UP: {len(X_train_up)} samples ({len(X_train_up)/len(X_train)*100:.1f}%)")
        print(f"  └─ DOWN: {len(X_train_down)} samples ({len(X_train_down)/len(X_train)*100:.1f}%)")
        print(f"Validation set: {len(X_val)} samples")
        print(f"  └─ UP: {len(X_val_up)} samples ({len(X_val_up)/len(X_val)*100:.1f}%)")
        print(f"  └─ DOWN: {len(X_val_down)} samples ({len(X_val_down)/len(X_val)*100:.1f}%)")
        print(f"Test set: {len(X_test)} samples")
        print(f"  └─ UP: {len(X_test_up)} samples ({len(X_test_up)/len(X_test)*100:.1f}%)")
        print(f"  └─ DOWN: {len(X_test_down)} samples ({len(X_test_down)/len(X_test)*100:.1f}%)")

    # Calculate class weights for balancing
    class_weights_array = compute_class_weight('balanced', classes=np.unique(y_dir_train), y=y_dir_train)
    class_weight_dict = {0: class_weights_array[0], 1: class_weights_array[1]}
    
    if verbose:
        print(f"\nClass weights: DOWN={class_weight_dict[0]:.3f}, UP={class_weight_dict[1]:.3f}")

    # =========================================================================
    # DIRECTION MODELS (Unchanged)
    # =========================================================================
    direction_models = {
        "Logistic Regression": LogisticRegression(
            class_weight='balanced',
            max_iter=1000, 
            random_state=42
        ),
        "XGBoost": XGBClassifier(
            n_estimators=300, 
            learning_rate=0.03, 
            max_depth=4, 
            subsample=0.8, 
            colsample_bytree=0.8,
            scale_pos_weight=class_weight_dict[1]/class_weight_dict[0],
            eval_metric='logloss',
            random_state=42, 
            n_jobs=1
        ),
        "CatBoost": CatBoostClassifier(
            iterations=300, 
            depth=6, 
            learning_rate=0.03,
            l2_leaf_reg=5,
            class_weights=class_weight_dict,
            verbose=False, 
            random_state=42,
            allow_writing_files=False
        ),
        "HistGradient": HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.03,
            max_depth=6,
            l2_regularization=1.0,
            random_state=42
        )
    }
    
    if LIGHTGBM_AVAILABLE:
        direction_models["LightGBM"] = LGBMClassifier(
            n_estimators=300, 
            learning_rate=0.03, 
            max_depth=5, 
            class_weight='balanced', 
            random_state=42, 
            verbose=-1,
            n_jobs=1
        )

    # =========================================================================
    # MAGNITUDE MODELS (Same architecture for both UP and DOWN)
    # =========================================================================
    def get_magnitude_models():
        """Factory function to create fresh model instances"""
        models = {
            "Ridge": Ridge(alpha=1.0, random_state=42),
            "XGBoost": XGBRegressor(
                n_estimators=300, 
                learning_rate=0.03, 
                max_depth=4, 
                subsample=0.8, 
                objective="reg:squarederror", 
                random_state=42,
                n_jobs=1
            ),
            "CatBoost": CatBoostRegressor(
                iterations=300, 
                depth=6, 
                learning_rate=0.03, 
                l2_leaf_reg=5,
                verbose=False, 
                random_state=42,
                allow_writing_files=False
            ),
            "HistGradient": HistGradientBoostingRegressor(
                max_iter=300,
                learning_rate=0.03,
                max_depth=6,
                l2_regularization=1.0,
                random_state=42
            )
        }
        
        if LIGHTGBM_AVAILABLE:
            models["LightGBM"] = LGBMRegressor(
                n_estimators=300, 
                learning_rate=0.03, 
                max_depth=5, 
                random_state=42, 
                verbose=-1,
                n_jobs=1
            )
        
        return models

    # Train direction models
    if verbose:
        print(f"\n{'='*60}")
        print("TRAINING DIRECTION MODELS (Up/Down)")
        print("="*60)
    
    n_jobs_parallel = -1 if not (os.environ.get('RENDER') or os.environ.get('CI')) else 1
    
    dir_results = Parallel(n_jobs=n_jobs_parallel, backend='threading', verbose=0)(
        delayed(train_direction_model)(
            name, model, X_train, y_dir_train, X_val, y_dir_val, X_test, y_dir_test,
            StandardScaler() if name in MODELS_NEEDING_SCALING else None
        )
        for name, model in direction_models.items()
    )

    dir_report = {}
    dir_trained_models = []
    dir_scalers = {}

    for name, model, metrics, scaler in dir_results:
        if model is None or metrics is None:
            continue
            
        dir_report[name] = metrics
        dir_trained_models.append((name, model))
        if scaler is not None:
            dir_scalers[name] = scaler
        
        if verbose:
            print(
                f"{name:25} | "
                f"Val Acc: {metrics['validation']['Accuracy']:.4f}, F1: {metrics['validation']['F1']:.4f} | "
                f"Test Acc: {metrics['test']['Accuracy']:.4f}, F1: {metrics['test']['F1']:.4f}"
            )

    # =========================================================================
    # TRAIN UP MAGNITUDE MODELS (Escalator Up Specialists)
    # =========================================================================
    if verbose:
        print(f"\n{'='*60}")
        print("TRAINING UP-MAGNITUDE MODELS (Escalator Up)")
        print(f"Training on {len(X_train_up)} UP days")
        print("="*60)
    
    magnitude_models_up = get_magnitude_models()
    
    mag_up_results = Parallel(n_jobs=n_jobs_parallel, backend='threading', verbose=0)(
        delayed(train_magnitude_model)(
            name, model, 
            X_train_up, y_mag_train_up,
            X_val_up, y_mag_val_up,
            X_test_up, y_mag_test_up,
            StandardScaler() if name in MODELS_NEEDING_SCALING else None
        )
        for name, model in magnitude_models_up.items()
    )

    mag_up_report = {}
    mag_up_trained_models = []
    mag_up_scalers = {}

    for name, model, metrics, scaler in mag_up_results:
        if model is None or metrics is None:
            continue
            
        mag_up_report[name] = metrics
        mag_up_trained_models.append((name, model))
        if scaler is not None:
            mag_up_scalers[name] = scaler
        
        if verbose:
            print(
                f"{name:25} | "
                f"Val R²: {metrics['validation']['R²']:.4f}, MAE: {metrics['validation']['MAE']:.3f}% | "
                f"Test R²: {metrics['test']['R²']:.4f}, MAE: {metrics['test']['MAE']:.3f}%"
            )

    # =========================================================================
    # TRAIN DOWN MAGNITUDE MODELS (Elevator Down Specialists)
    # =========================================================================
    if verbose:
        print(f"\n{'='*60}")
        print("TRAINING DOWN-MAGNITUDE MODELS (Elevator Down)")
        print(f"Training on {len(X_train_down)} DOWN days")
        print("="*60)
    
    magnitude_models_down = get_magnitude_models()
    
    mag_down_results = Parallel(n_jobs=n_jobs_parallel, backend='threading', verbose=0)(
        delayed(train_magnitude_model)(
            name, model,
            X_train_down, y_mag_train_down,
            X_val_down, y_mag_val_down,
            X_test_down, y_mag_test_down,
            StandardScaler() if name in MODELS_NEEDING_SCALING else None
        )
        for name, model in magnitude_models_down.items()
    )

    mag_down_report = {}
    mag_down_trained_models = []
    mag_down_scalers = {}

    for name, model, metrics, scaler in mag_down_results:
        if model is None or metrics is None:
            continue
            
        mag_down_report[name] = metrics
        mag_down_trained_models.append((name, model))
        if scaler is not None:
            mag_down_scalers[name] = scaler
        
        if verbose:
            print(
                f"{name:25} | "
                f"Val R²: {metrics['validation']['R²']:.4f}, MAE: {metrics['validation']['MAE']:.3f}% | "
                f"Test R²: {metrics['test']['R²']:.4f}, MAE: {metrics['test']['MAE']:.3f}%"
            )

    # =========================================================================
    # SELECT BEST MODELS
    # =========================================================================
    
    # Best direction model
    best_dir_name = max(dir_report, key=lambda x: dir_report[x]["validation"]["F1"])
    best_dir_model = next(m for n, m in dir_trained_models if n == best_dir_name)
    best_dir_scaler = dir_scalers.get(best_dir_name, None)
    
    # Best UP magnitude model
    best_mag_up_name = max(mag_up_report, key=lambda x: mag_up_report[x]["validation"]["R²"])
    best_mag_up_model = next(m for n, m in mag_up_trained_models if n == best_mag_up_name)
    best_mag_up_scaler = mag_up_scalers.get(best_mag_up_name, None)
    
    # Best DOWN magnitude model
    best_mag_down_name = max(mag_down_report, key=lambda x: mag_down_report[x]["validation"]["R²"])
    best_mag_down_model = next(m for n, m in mag_down_trained_models if n == best_mag_down_name)
    best_mag_down_scaler = mag_down_scalers.get(best_mag_down_name, None)

    # =========================================================================
    # CREATE ENSEMBLES
    # =========================================================================
    
    # Direction ensemble (exclude Logistic Regression)
    ensemble_candidates = [(name, metrics) for name, metrics in dir_report.items() if name != "Logistic Regression"]
    top_dir_models = sorted(
        ensemble_candidates,
        key=lambda x: x[1]["validation"]["F1"],
        reverse=True
    )[:3]
    
    dir_ensemble = None
    if len(top_dir_models) > 1:
        total_f1 = sum(m[1]["validation"]["F1"] for m in top_dir_models)
        dir_ensemble = {
            "models": [next(m for n, m in dir_trained_models if n == name) for name, _ in top_dir_models],
            "weights": [m[1]["validation"]["F1"] / total_f1 for m in top_dir_models],
            "scalers": [dir_scalers.get(name, None) for name, _ in top_dir_models],
            "model_names": [name for name, _ in top_dir_models]
        }
    
    # UP magnitude ensemble (exclude Ridge)
    mag_up_candidates = [(name, metrics) for name, metrics in mag_up_report.items() if name != "Ridge"]
    top_mag_up = sorted(
        [m for m in mag_up_candidates if m[1]["validation"]["R²"] > 0],
        key=lambda x: x[1]["validation"]["R²"],
        reverse=True
    )[:3]
    
    mag_up_ensemble = None
    if len(top_mag_up) > 1:
        total_r2 = sum(m[1]["validation"]["R²"] for m in top_mag_up)
        mag_up_ensemble = {
            "models": [next(m for n, m in mag_up_trained_models if n == name) for name, _ in top_mag_up],
            "weights": [m[1]["validation"]["R²"] / total_r2 for m in top_mag_up],
            "scalers": [mag_up_scalers.get(name, None) for name, _ in top_mag_up],
            "model_names": [name for name, _ in top_mag_up]
        }

    # DOWN magnitude ensemble (exclude Ridge)
    mag_down_candidates = [(name, metrics) for name, metrics in mag_down_report.items() if name != "Ridge"]
    top_mag_down = sorted(
        [m for m in mag_down_candidates if m[1]["validation"]["R²"] > 0],
        key=lambda x: x[1]["validation"]["R²"],
        reverse=True
    )[:3]
    
    mag_down_ensemble = None
    if len(top_mag_down) > 1:
        total_r2 = sum(m[1]["validation"]["R²"] for m in top_mag_down)
        mag_down_ensemble = {
            "models": [next(m for n, m in mag_down_trained_models if n == name) for name, _ in top_mag_down],
            "weights": [m[1]["validation"]["R²"] / total_r2 for m in top_mag_down],
            "scalers": [mag_down_scalers.get(name, None) for name, _ in top_mag_down],
            "model_names": [name for name, _ in top_mag_down]
        }

    # Determine confidence
    dir_f1 = dir_report[best_dir_name]["validation"]["F1"]
    mag_up_r2 = mag_up_report[best_mag_up_name]["validation"]["R²"]
    mag_down_r2 = mag_down_report[best_mag_down_name]["validation"]["R²"]
    
    # Average magnitude confidence
    avg_mag_r2 = (mag_up_r2 + mag_down_r2) / 2
    
    if dir_f1 > 0.6 and avg_mag_r2 > 0.3:
        confidence = "high"
    elif dir_f1 > 0.55 and avg_mag_r2 > 0.15:
        confidence = "medium"
    else:
        confidence = "low"

    if verbose:
        print(f"\n{'='*60}")
        print("BEST MODELS SUMMARY")
        print("="*60)
        print(f"\nDirection Model: {best_dir_name}")
        print(f"  Val F1: {dir_f1:.4f}")
        
        print(f"\nUP Magnitude Model: {best_mag_up_name}")
        print(f"  Val R²: {mag_up_r2:.4f}")
        
        print(f"\nDOWN Magnitude Model: {best_mag_down_name}")
        print(f"  Val R²: {mag_down_r2:.4f}")
        
        print(f"\nOverall Confidence: {confidence.upper()}")
        print("="*60)

    result = {
        "direction": {
            "best_model": best_dir_model,
            "best_model_name": best_dir_name,
            "scaler": best_dir_scaler,
            "metrics": dir_report[best_dir_name],
            "report": dir_report,
            "ensemble": dir_ensemble
        },
        "magnitude": {
            "conditional": True,
            "up": {
                "best_model": best_mag_up_model,
                "best_model_name": best_mag_up_name,
                "scaler": best_mag_up_scaler,
                "metrics": mag_up_report[best_mag_up_name],
                "report": mag_up_report,
                "ensemble": mag_up_ensemble
            },
            "down": {
                "best_model": best_mag_down_model,
                "best_model_name": best_mag_down_name,
                "scaler": best_mag_down_scaler,
                "metrics": mag_down_report[best_mag_down_name],
                "report": mag_down_report,
                "ensemble": mag_down_ensemble
            }
        },
        "confidence": confidence,
        "ticker": ticker,
        "latest_features": latest_features,
        "cached": False  # Newly trained model
    }
    
    # Add prediction function
    def predict(X_new):
        """Make predictions on new data using trained models."""
        return make_prediction(result, X_new)
    
    result["predict"] = predict
    
    # Save to cache if enabled
    if use_cache:
        _model_cache.save(ticker, result)
        if verbose:
            print(f"[CACHE] ✓ Models trained and cached for {ticker}")
    
    # Optionally return test data for analysis
    if return_data:
        result["test_data"] = {
            "X_test": X_test,
            "y_direction_test": y_dir_test,
            "full_X": X,
            "full_y_direction": y_direction
        }
    
    return result


def get_model_cache():
    """Get the global model cache instance for manual cache operations"""
    return _model_cache