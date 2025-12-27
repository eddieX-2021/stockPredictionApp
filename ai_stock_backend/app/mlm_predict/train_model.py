import numpy as np
import pandas as pd
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

# Optional: LightGBM
try:
    from lightgbm import LGBMClassifier, LGBMRegressor
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

# Models that benefit from scaling
MODELS_NEEDING_SCALING = {"Logistic Regression", "Ridge", "MLP"}


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
    Make a complete prediction using both direction and magnitude models.
    
    Combines direction and magnitude intelligently:
    1. Get direction (UP/DOWN) with confidence
    2. Get magnitude (absolute % change)
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
    
    # Get magnitude prediction (absolute value)
    if mag_info["ensemble"]:
        magnitude_pred = predict_ensemble_magnitude(X_new, mag_info["ensemble"])
    else:
        X_proc = mag_info["scaler"].transform(X_new) if mag_info["scaler"] else X_new
        magnitude_pred = mag_info["best_model"].predict(X_proc)
    
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
                "magnitude": mag_info["ensemble"] is not None
            }
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
                "magnitude": mag_info["ensemble"] is not None
            }
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


def train_stock_models(ticker, start_date, end_date, verbose=True, return_data=False):
    """
    Train dual prediction system: direction (up/down) and magnitude (% change).
    Returns comprehensive results for both models plus prediction function.
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date for training data (YYYY-MM-DD)
        end_date: End date for training data (YYYY-MM-DD)
        verbose: Whether to print detailed training logs
        return_data: If True, return X, y_direction for testing purposes
    
    Returns:
        Dictionary containing:
        - direction: Direction model info and metrics
        - magnitude: Magnitude model info and metrics
        - confidence: Overall system confidence (high/medium/low)
        - ticker: Stock ticker
        - predict: Function to make predictions on new data
        - test_data: (optional) Test set data for evaluation
    """
    stock_data = fetch_raw_stock_data(ticker, start_date, end_date)
    if stock_data is None:
        if verbose:
            print("Failed to fetch data.")
        return None

    # Extended training window
    stock_data = stock_data.tail(1250)

    X, y_price, stock_data = generate_features(stock_data)
    if X is None or y_price is None:
        if verbose:
            print("Failed to generate features.")
        return None

    # Align the data
    X = X.iloc[:-1]
    y_price = y_price.iloc[:-1]
    current_prices = stock_data['Close'].iloc[:-1].values
    
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

    if verbose:
        print(f"Training set: {len(X_train)} samples")
        print(f"Validation set: {len(X_val)} samples")
        print(f"Test set: {len(X_test)} samples")
        print(f"Direction class balance (training): Up={sum(y_dir_train)}/{len(y_dir_train)} ({sum(y_dir_train)/len(y_dir_train)*100:.1f}%)\n")

    # Calculate class weights for balancing
    class_weights_array = compute_class_weight('balanced', classes=np.unique(y_dir_train), y=y_dir_train)
    class_weight_dict = {0: class_weights_array[0], 1: class_weights_array[1]}
    
    if verbose:
        print(f"Class weights: DOWN={class_weight_dict[0]:.3f}, UP={class_weight_dict[1]:.3f}\n")

    # Direction models with class balancing
    direction_models = {
        "Logistic Regression": LogisticRegression(
            class_weight='balanced',
            max_iter=1000, 
            random_state=42
        ),
        "Random Forest": RandomForestClassifier(
            class_weight='balanced',
            n_estimators=200, 
            max_depth=10, 
            min_samples_split=5, 
            random_state=42
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=150, 
            learning_rate=0.05, 
            max_depth=5, 
            random_state=42
        ),
        "HistGradient Boosting": HistGradientBoostingClassifier(
            max_iter=150, 
            learning_rate=0.05, 
            max_depth=10, 
            random_state=42
        ),
        "XGBoost": XGBClassifier(
            n_estimators=150, 
            learning_rate=0.05, 
            max_depth=6,
            scale_pos_weight=class_weight_dict[1]/class_weight_dict[0],
            random_state=42, 
            eval_metric='logloss'
        ),
        "CatBoost": CatBoostClassifier(
            iterations=150, 
            depth=8, 
            learning_rate=0.05,
            class_weights=class_weight_dict,
            verbose=False, 
            random_state=42
        ),
        "MLP": MLPClassifier(
            hidden_layer_sizes=(100, 50), 
            max_iter=500, 
            random_state=42
        )
    }
    
    if LIGHTGBM_AVAILABLE:
        direction_models["LightGBM"] = LGBMClassifier(
            n_estimators=150, 
            learning_rate=0.05, 
            max_depth=8,
            class_weight='balanced',
            random_state=42, 
            verbose=-1
        )

    # Magnitude models
    magnitude_models = {
        "Ridge": Ridge(alpha=1.0, random_state=42),
        "Random Forest": RandomForestRegressor(
            n_estimators=200, max_depth=10, min_samples_split=5, random_state=42
        ),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=150, learning_rate=0.05, max_depth=5, random_state=42
        ),
        "HistGradient Boosting": HistGradientBoostingRegressor(
            max_iter=150, learning_rate=0.05, max_depth=10, random_state=42
        ),
        "XGBoost": XGBRegressor(
            n_estimators=150, learning_rate=0.05, max_depth=6,
            objective="reg:squarederror", random_state=42
        ),
        "CatBoost": CatBoostRegressor(
            iterations=150, depth=8, learning_rate=0.05,
            verbose=False, random_state=42
        ),
        "MLP": MLPRegressor(
            hidden_layer_sizes=(100, 50), max_iter=500, random_state=42
        )
    }
    
    if LIGHTGBM_AVAILABLE:
        magnitude_models["LightGBM"] = LGBMRegressor(
            n_estimators=150, learning_rate=0.05, max_depth=8,
            random_state=42, verbose=-1
        )

    # Train direction models
    if verbose:
        print("="*60)
        print("TRAINING DIRECTION MODELS (Up/Down)")
        print("="*60)
    
    n_jobs = min(len(direction_models), os.cpu_count() or 1)
    
    dir_results = Parallel(n_jobs=n_jobs, backend='threading', verbose=0)(
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

    # Train magnitude models
    if verbose:
        print(f"\n{'='*60}")
        print("TRAINING MAGNITUDE MODELS (% Change)")
        print("="*60)
    
    mag_results = Parallel(n_jobs=n_jobs, backend='threading', verbose=0)(
        delayed(train_magnitude_model)(
            name, model, X_train, y_mag_train, X_val, y_mag_val, X_test, y_mag_test,
            StandardScaler() if name in MODELS_NEEDING_SCALING else None
        )
        for name, model in magnitude_models.items()
    )

    mag_report = {}
    mag_trained_models = []
    mag_scalers = {}

    for name, model, metrics, scaler in mag_results:
        if model is None or metrics is None:
            continue
            
        mag_report[name] = metrics
        mag_trained_models.append((name, model))
        if scaler is not None:
            mag_scalers[name] = scaler
        
        if verbose:
            print(
                f"{name:25} | "
                f"Val R²: {metrics['validation']['R²']:.4f}, MAE: {metrics['validation']['MAE']:.3f}% | "
                f"Test R²: {metrics['test']['R²']:.4f}, MAE: {metrics['test']['MAE']:.3f}%"
            )

    # Select best models
    best_dir_name = max(dir_report, key=lambda x: dir_report[x]["validation"]["F1"])
    best_dir_model = next(m for n, m in dir_trained_models if n == best_dir_name)
    best_dir_scaler = dir_scalers.get(best_dir_name, None)
    
    best_mag_name = max(mag_report, key=lambda x: mag_report[x]["validation"]["R²"])
    best_mag_model = next(m for n, m in mag_trained_models if n == best_mag_name)
    best_mag_scaler = mag_scalers.get(best_mag_name, None)

    # Create ensembles
    top_dir_models = sorted(
        [(name, metrics) for name, metrics in dir_report.items()],
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
    
    top_mag_models = sorted(
        [(name, metrics) for name, metrics in mag_report.items()
         if metrics["validation"]["R²"] > 0],
        key=lambda x: x[1]["validation"]["R²"],
        reverse=True
    )[:3]
    
    mag_ensemble = None
    if len(top_mag_models) > 1:
        total_r2 = sum(m[1]["validation"]["R²"] for m in top_mag_models)
        mag_ensemble = {
            "models": [next(m for n, m in mag_trained_models if n == name) for name, _ in top_mag_models],
            "weights": [m[1]["validation"]["R²"] / total_r2 for m in top_mag_models],
            "scalers": [mag_scalers.get(name, None) for name, _ in top_mag_models],
            "model_names": [name for name, _ in top_mag_models]
        }

    # Determine confidence
    dir_f1 = dir_report[best_dir_name]["validation"]["F1"]
    mag_r2 = mag_report[best_mag_name]["validation"]["R²"]
    
    if dir_f1 > 0.6 and mag_r2 > 0.3:
        confidence = "high"
    elif dir_f1 > 0.55 and mag_r2 > 0.15:
        confidence = "medium"
    else:
        confidence = "low"

    if verbose:
        print(f"\n{'='*60}")
        print("BEST MODELS SUMMARY")
        print("="*60)
        print(f"\nDirection Model: {best_dir_name}")
        print(f"  Val - Accuracy: {dir_report[best_dir_name]['validation']['Accuracy']:.4f}, F1: {dir_report[best_dir_name]['validation']['F1']:.4f}")
        print(f"  Test - Accuracy: {dir_report[best_dir_name]['test']['Accuracy']:.4f}, F1: {dir_report[best_dir_name]['test']['F1']:.4f}")
        
        print(f"\nMagnitude Model: {best_mag_name}")
        print(f"  Val - R²: {mag_report[best_mag_name]['validation']['R²']:.4f}, MAE: {mag_report[best_mag_name]['validation']['MAE']:.3f}%")
        print(f"  Test - R²: {mag_report[best_mag_name]['test']['R²']:.4f}, MAE: {mag_report[best_mag_name]['test']['MAE']:.3f}%")
        
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
            "best_model": best_mag_model,
            "best_model_name": best_mag_name,
            "scaler": best_mag_scaler,
            "metrics": mag_report[best_mag_name],
            "report": mag_report,
            "ensemble": mag_ensemble
        },
        "confidence": confidence,
        "ticker": ticker
    }
    
    # Add prediction function as a method
    def predict(X_new):
        """Make predictions on new data using trained models."""
        return make_prediction(result, X_new)
    
    result["predict"] = predict
    
    # Optionally return test data for analysis
    if return_data:
        result["test_data"] = {
            "X_test": X_test,
            "y_direction_test": y_dir_test,
            "full_X": X,
            "full_y_direction": y_direction
        }
    
    return result