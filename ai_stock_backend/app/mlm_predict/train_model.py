import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, AdaBoostRegressor
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import r2_score, mean_squared_error
from xgboost import XGBRegressor
from catboost import CatBoostRegressor
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from joblib import Parallel, delayed
import os
from app.services.fetch_data import fetch_raw_stock_data, generate_features

# Models that benefit from scaling
MODELS_NEEDING_SCALING = {"Linear Regression", "SVR"}

# Models that need Close price normalized
MODELS_NEEDING_CLOSE_NORMALIZATION = {
    "Decision Tree", "Random Forest", "Gradient Boosting", 
    "AdaBoost", "XGBRegressor", "CatBoost"
}

# -----------------------------
# Train + evaluate a single model
# -----------------------------
def train_and_evaluate(name, model, X_train, y_train, X_val, y_val, X_test, y_test, avg_price, scaler=None):
    """
    Train and evaluate a single model with proper error handling.
    Target is next-day price, NRMSE normalized by average price.
    
    For tree-based models, we normalize the Close price by dividing by training mean
    to help them generalize across different price ranges.
    """
    print(f"Training {name}...")
    
    try:
        # Make copies to avoid modifying original data
        X_train_proc = X_train.copy()
        X_val_proc = X_val.copy()
        X_test_proc = X_test.copy()
        
        # For tree models, normalize Close price by training average
        if name in MODELS_NEEDING_CLOSE_NORMALIZATION:
            train_close_mean = X_train_proc['Close'].mean()
            X_train_proc['Close'] = X_train_proc['Close'] / train_close_mean
            X_val_proc['Close'] = X_val_proc['Close'] / train_close_mean
            X_test_proc['Close'] = X_test_proc['Close'] / train_close_mean
            
            # Also normalize target for tree models
            y_train_norm = y_train / train_close_mean
            y_val_norm = y_val / train_close_mean
            y_test_norm = y_test / train_close_mean
        else:
            y_train_norm = y_train
            y_val_norm = y_val
            y_test_norm = y_test
        
        # Apply scaling for Linear/SVR models
        if name in MODELS_NEEDING_SCALING and scaler is not None:
            X_train_proc = scaler.fit_transform(X_train_proc)
            X_val_proc = scaler.transform(X_val_proc)
            X_test_proc = scaler.transform(X_test_proc)
        
        # Train model
        model.fit(X_train_proc, y_train_norm)
        
        # Evaluate on validation set (for model selection)
        y_val_pred_norm = model.predict(X_val_proc)
        
        # Denormalize predictions for tree models
        if name in MODELS_NEEDING_CLOSE_NORMALIZATION:
            y_val_pred = y_val_pred_norm * train_close_mean
        else:
            y_val_pred = y_val_pred_norm
            
        val_r2 = r2_score(y_val, y_val_pred)
        val_mse = mean_squared_error(y_val, y_val_pred)
        val_rmse = np.sqrt(val_mse)
        val_nrmse = (val_rmse / avg_price) * 100
        
        # Evaluate on test set (for final reporting)
        y_test_pred_norm = model.predict(X_test_proc)
        
        # Denormalize predictions for tree models
        if name in MODELS_NEEDING_CLOSE_NORMALIZATION:
            y_test_pred = y_test_pred_norm * train_close_mean
        else:
            y_test_pred = y_test_pred_norm
            
        test_r2 = r2_score(y_test, y_test_pred)
        test_mse = mean_squared_error(y_test, y_test_pred)
        test_rmse = np.sqrt(test_mse)
        test_nrmse = (test_rmse / avg_price) * 100
        
        return name, model, {
            "validation": {
                "R²": val_r2,
                "MSE": val_mse,
                "RMSE": val_rmse,
                "NRMSE (%)": val_nrmse
            },
            "test": {
                "R²": test_r2,
                "MSE": test_mse,
                "RMSE": test_rmse,
                "NRMSE (%)": test_nrmse
            }
        }, scaler if name in MODELS_NEEDING_SCALING else None
        
    except Exception as e:
        print(f"Failed to train {name}: {e}")
        return name, None, None, None

# -----------------------------
# Main training function
# -----------------------------
def train_stock_models(ticker, start_date, end_date):
    """
    Train multiple models and select the best one based on validation performance.
    Returns comprehensive results including best model, scaler, and all metrics.
    """
    stock_data = fetch_raw_stock_data(ticker, start_date, end_date)
    if stock_data is None:
        print("Failed to fetch data.")
        return None

    # Extended training window for better model performance
    stock_data = stock_data.tail(1250)  # ~5 years of data

    X, y, stock_data = generate_features(stock_data)
    if X is None or y is None:
        print("Failed to generate features.")
        return None

    # Sequential split to preserve temporal ordering (critical for time series)
    # 60% train, 20% validation, 20% test
    n = len(X)
    train_end = int(n * 0.6)
    val_end = int(n * 0.8)
    
    X_train = X[:train_end]
    y_train = y[:train_end]
    
    X_val = X[train_end:val_end]
    y_val = y[train_end:val_end]
    
    X_test = X[val_end:]
    y_test = y[val_end:]

    # Calculate average price from training data only (avoid data leakage)
    avg_stock_price = y_train.mean()

    print(f"Training set: {len(X_train)} samples")
    print(f"Validation set: {len(X_val)} samples")
    print(f"Test set: {len(X_test)} samples")
    print(f"Average stock price (training): ${avg_stock_price:.2f}\n")

    models = {
        "Linear Regression": LinearRegression(),
        "Decision Tree": DecisionTreeRegressor(max_depth=8, random_state=42),
        "Random Forest": RandomForestRegressor(
            n_estimators=100, max_depth=8, random_state=42
        ),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=100, learning_rate=0.05, random_state=42
        ),
        "AdaBoost": AdaBoostRegressor(
            n_estimators=100, learning_rate=0.05, random_state=42
        ),
        "SVR": SVR(kernel="rbf", C=1.0, epsilon=0.1),
        "XGBRegressor": XGBRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=5,
            objective="reg:squarederror",
            random_state=42
        ),
        "CatBoost": CatBoostRegressor(
            iterations=100,
            depth=8,
            learning_rate=0.05,
            verbose=False,
            random_state=42
        )
    }

    # Parallel training - use all available cores
    n_jobs = min(len(models), os.cpu_count() or 1)
    
    results = Parallel(n_jobs=n_jobs)(
        delayed(train_and_evaluate)(
            name,
            model,
            X_train,
            y_train,
            X_val,
            y_val,
            X_test,
            y_test,
            avg_stock_price,
            StandardScaler() if name in MODELS_NEEDING_SCALING else None
        )
        for name, model in models.items()
    )

    model_report = {}
    trained_models = []
    model_scalers = {}

    for name, model, metrics, scaler in results:
        if model is None or metrics is None:
            continue
            
        model_report[name] = metrics
        trained_models.append((name, model))
        if scaler is not None:
            model_scalers[name] = scaler
        
        print(
            f"{name} | "
            f"Val R²: {metrics['validation']['R²']:.4f}, "
            f"Val NRMSE: {metrics['validation']['NRMSE (%)']:.2f}% | "
            f"Test R²: {metrics['test']['R²']:.4f}, "
            f"Test NRMSE: {metrics['test']['NRMSE (%)']:.2f}%"
        )

    if not model_report:
        print("All models failed to train.")
        return None

    # Select best model based on VALIDATION R² (not test set)
    best_model_name = max(model_report, key=lambda x: model_report[x]["validation"]["R²"])
    best_model = next(m for n, m in trained_models if n == best_model_name)
    best_scaler = model_scalers.get(best_model_name, None)

    print(
        f"\n{'='*60}\n"
        f"Best Model: {best_model_name}\n"
        f"Validation - R²: {model_report[best_model_name]['validation']['R²']:.4f}, "
        f"NRMSE: {model_report[best_model_name]['validation']['NRMSE (%)']:.2f}%\n"
        f"Test - R²: {model_report[best_model_name]['test']['R²']:.4f}, "
        f"NRMSE: {model_report[best_model_name]['test']['NRMSE (%)']:.2f}%\n"
        f"{'='*60}"
    )

    return {
        "best_model": best_model,
        "best_model_name": best_model_name,
        "scaler": best_scaler,
        "model_report": model_report,
        "metrics": model_report[best_model_name],
        "avg_price": avg_stock_price
    }