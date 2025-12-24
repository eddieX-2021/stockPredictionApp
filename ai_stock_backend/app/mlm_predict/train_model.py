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
from joblib import Parallel, delayed
import os
from app.services.fetch_data import fetch_raw_stock_data, generate_features

# Optional: LightGBM (install with: pip install lightgbm)
try:
    from lightgbm import LGBMClassifier, LGBMRegressor
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("Note: LightGBM not available. Install with: pip install lightgbm")

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
    
    # Collect weighted probability predictions
    weighted_probs = np.zeros(len(X))
    
    for i, (model, scaler, name) in enumerate(zip(models, scalers, model_names)):
        X_proc = scaler.transform(X) if scaler is not None else X
        
        # Get probability of upward movement (class 1)
        if hasattr(model, "predict_proba"):
            prob = model.predict_proba(X_proc)[:, 1]
        else:
            prob = model.predict(X_proc)
        
        weighted_probs += prob * weights[i]
    
    # Convert to binary predictions
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


def train_direction_model(name, model, X_train, y_train, X_val, y_val, X_test, y_test, scaler=None):
    """Train and evaluate a classification model for direction prediction."""
    try:
        # Apply scaling if needed
        if name in MODELS_NEEDING_SCALING and scaler is not None:
            X_train_proc = scaler.fit_transform(X_train)
            X_val_proc = scaler.transform(X_val)
            X_test_proc = scaler.transform(X_test)
        else:
            X_train_proc = X_train
            X_val_proc = X_val
            X_test_proc = X_test
        
        # Train model
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
        # Apply scaling if needed
        if name in MODELS_NEEDING_SCALING and scaler is not None:
            X_train_proc = scaler.fit_transform(X_train)
            X_val_proc = scaler.transform(X_val)
            X_test_proc = scaler.transform(X_test)
        else:
            X_train_proc = X_train
            X_val_proc = X_val
            X_test_proc = X_test
        
        # Train model
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


def train_stock_models(ticker, start_date, end_date):
    """
    Train dual prediction system: direction (up/down) and magnitude (% change).
    Returns comprehensive results for both models.
    """
    stock_data = fetch_raw_stock_data(ticker, start_date, end_date)
    if stock_data is None:
        print("Failed to fetch data.")
        return None

    # Extended training window
    stock_data = stock_data.tail(1250)

    X, y_price, stock_data = generate_features(stock_data)
    if X is None or y_price is None:
        print("Failed to generate features.")
        return None

    # Align the data - remove last row from X and current prices since target is shifted
    X = X.iloc[:-1]  # Remove last row since we don't have a target for it
    y_price = y_price.iloc[:-1]  # This is actually next day's price
    current_prices = stock_data['Close'].iloc[:-1].values
    
    # Create direction target (1 = up, 0 = down)
    # y_price already contains next day's prices due to shift(-1) in generate_features
    y_direction = (y_price.values > current_prices).astype(int)
    
    # Create magnitude target (percentage change)
    y_magnitude = ((y_price.values - current_prices) / current_prices) * 100

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

    print(f"Training set: {len(X_train)} samples")
    print(f"Validation set: {len(X_val)} samples")
    print(f"Test set: {len(X_test)} samples")
    print(f"Direction class balance (training): Up={sum(y_dir_train)}/{len(y_dir_train)} ({sum(y_dir_train)/len(y_dir_train)*100:.1f}%)\n")

    # ==========================================
    # DIRECTION MODELS (Classification)
    # ==========================================
    
    direction_models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_split=5, random_state=42
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=150, learning_rate=0.05, max_depth=5, random_state=42
        ),
        "HistGradient Boosting": HistGradientBoostingClassifier(
            max_iter=150, learning_rate=0.05, max_depth=10, random_state=42
        ),
        "XGBoost": XGBClassifier(
            n_estimators=150, learning_rate=0.05, max_depth=6,
            random_state=42, eval_metric='logloss'
        ),
        "CatBoost": CatBoostClassifier(
            iterations=150, depth=8, learning_rate=0.05,
            verbose=False, random_state=42
        ),
        "MLP": MLPClassifier(
            hidden_layer_sizes=(100, 50), max_iter=500, random_state=42
        )
    }
    
    # Add LightGBM if available
    if LIGHTGBM_AVAILABLE:
        direction_models["LightGBM"] = LGBMClassifier(
            n_estimators=150, learning_rate=0.05, max_depth=8,
            random_state=42, verbose=-1
        )

    # ==========================================
    # MAGNITUDE MODELS (Regression)
    # ==========================================
    
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
    
    # Add LightGBM if available
    if LIGHTGBM_AVAILABLE:
        magnitude_models["LightGBM"] = LGBMRegressor(
            n_estimators=150, learning_rate=0.05, max_depth=8,
            random_state=42, verbose=-1
        )

    # Train direction models
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
        
        print(
            f"{name:25} | "
            f"Val Acc: {metrics['validation']['Accuracy']:.4f}, F1: {metrics['validation']['F1']:.4f} | "
            f"Test Acc: {metrics['test']['Accuracy']:.4f}, F1: {metrics['test']['F1']:.4f}"
        )

    # Train magnitude models
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

    return {
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