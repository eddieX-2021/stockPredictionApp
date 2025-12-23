import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, AdaBoostRegressor
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import r2_score, mean_squared_error
from xgboost import XGBRegressor
from catboost import CatBoostRegressor
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from joblib import Parallel, delayed
from app.services.fetch_data import fetch_raw_stock_data, generate_features

# -----------------------------
# Train + evaluate a single model
# -----------------------------
def train_and_evaluate(name, model, X_train, y_train, X_test, y_test, avg_price):
    print(f"Training {name}...")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    nrmse = (rmse / avg_price) * 100

    return name, model, {
        "R²": r2,
        "MSE": mse,
        "RMSE": rmse,
        "NRMSE (%)": nrmse
    }

# -----------------------------
# Main training function
# -----------------------------
def train_stock_models(ticker, start_date, end_date):
    stock_data = fetch_raw_stock_data(ticker, start_date, end_date)
    if stock_data is None:
        print("Failed to fetch data.")
        return None, None

    # Training window
    stock_data = stock_data.tail(750)

    X, y, stock_data = generate_features(stock_data)
    if X is None or y is None:
        print("Failed to generate features.")
        return None, None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    avg_stock_price = stock_data["Close"].mean().item()

    models = {
        "Linear Regression": LinearRegression(),
        "Decision Tree": DecisionTreeRegressor(max_depth=8),
        "Random Forest": RandomForestRegressor(
            n_estimators=100, max_depth=8, random_state=42
        ),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=100, learning_rate=0.05
        ),
        "AdaBoost": AdaBoostRegressor(
            n_estimators=100, learning_rate=0.05
        ),
        "SVR": SVR(kernel="rbf", C=1.0, epsilon=0.1),
        "XGBRegressor": XGBRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=5,
            objective="reg:squarederror"
        ),
        "CatBoost": CatBoostRegressor(
            iterations=100,
            depth=8,
            learning_rate=0.05,
            verbose=False
        )
    }

    # Parallel training
    results = Parallel(n_jobs=3)(
        delayed(train_and_evaluate)(
            name,
            model,
            X_train_scaled,
            y_train,
            X_test_scaled,
            y_test,
            avg_stock_price
        )
        for name, model in models.items()
    )

    model_report = {}
    trained_models = []

    for name, model, metrics in results:
        model_report[name] = metrics
        trained_models.append((name, model))
        print(
            f"{name} | R²: {metrics['R²']:.4f}, "
            f"RMSE: {metrics['RMSE']:.4f}, "
            f"NRMSE: {metrics['NRMSE (%)']:.2f}%"
        )

    # Select best model by R²
    best_model_name = max(model_report, key=lambda x: model_report[x]["R²"])
    best_model = next(m for n, m in trained_models if n == best_model_name)

    print(
        f"\nBest Model: {best_model_name} "
        f"(R² = {model_report[best_model_name]['R²']:.4f}, "
        f"NRMSE = {model_report[best_model_name]['NRMSE (%)']:.2f}%)"
    )

    return best_model, scaler