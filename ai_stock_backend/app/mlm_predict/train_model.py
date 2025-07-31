import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, AdaBoostRegressor
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.ensemble import StackingRegressor
from xgboost import XGBRegressor
from catboost import CatBoostRegressor
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
import pytz
from app.services.fetch_data import fetch_raw_stock_data, generate_features

# Function to evaluate models
def evaluate_models(X_train, y_train, X_test, y_test, models, params, stock_data, scaler):
    model_report = {}
    base_models = []
    
    avg_stock_price = stock_data['Close'].mean().item()
    
    for name, model in models.items():
        print(f"Training {name}...")
        grid = GridSearchCV(model, params[name], cv=3, scoring='r2', n_jobs=-1)
        grid.fit(X_train, y_train)
        best_model = grid.best_estimator_
        y_pred = best_model.predict(X_test)
        
        r2 = r2_score(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        nrmse = (rmse / avg_stock_price) * 100
        
        model_report[name] = {'R²': r2, 'MSE': mse, 'RMSE': rmse, 'NRMSE (%)': nrmse}
        print(f"{name} R² Score: {r2:.4f}, MSE: {mse:.4f}, RMSE: {rmse:.4f}, NRMSE: {nrmse:.2f}% (Best Params: {grid.best_params_})")
        base_models.append((name, best_model))
    
    print("Training Stacking Ensemble...")
    meta_model = RandomForestRegressor(n_estimators=50, random_state=42)
    stacking_model = StackingRegressor(estimators=base_models, final_estimator=meta_model, cv=3)
    stacking_model.fit(X_train, y_train)
    y_pred_stack = stacking_model.predict(X_test)
    
    stack_r2 = r2_score(y_test, y_pred_stack)
    stack_mse = mean_squared_error(y_test, y_pred_stack)
    stack_rmse = np.sqrt(stack_mse)
    stack_nrmse = (stack_rmse / avg_stock_price) * 100
    
    model_report["Stacking Ensemble"] = {
        'R²': stack_r2,
        'MSE': stack_mse,
        'RMSE': stack_rmse,
        'NRMSE (%)': stack_nrmse
    }
    print(f"Stacking Ensemble R² Score: {stack_r2:.4f}, MSE: {stack_mse:.4f}, RMSE: {stack_rmse:.4f}, NRMSE: {stack_nrmse:.2f}%")
    
    best_base_model_name = max((name for name in model_report if name != "Stacking Ensemble"), 
                              key=lambda x: model_report[x]['R²'])
    best_base_model = next(model for name, model in base_models if name == best_base_model_name)
    
    return model_report, best_base_model, scaler

# Main function to train and select the best model
def train_stock_models(ticker, start_date, end_date):
    stock_data = fetch_raw_stock_data(ticker, start_date, end_date)
    if stock_data is None:
        print("Failed to fetch data. Exiting.")
        return None, None

    X, y, stock_data = generate_features(stock_data)
    if X is None or y is None:
        print("Failed to generate features. Exiting.")
        return None, None

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    models = {
        "Random Forest": RandomForestRegressor(),
        "Decision Tree": DecisionTreeRegressor(),
        "Gradient Boosting": GradientBoostingRegressor(),
        "Linear Regression": LinearRegression(),
        "XGBRegressor": XGBRegressor(),
        "CatBoosting Regressor": CatBoostRegressor(verbose=False),
        "AdaBoost Regressor": AdaBoostRegressor(),
        "SVR": SVR()
    }

    params = {
        "Decision Tree": {'criterion': ['squared_error', 'absolute_error']},
        "Random Forest": {'n_estimators': [50, 100, 200]},
        "Gradient Boosting": {'n_estimators': [50, 100], 'learning_rate': [0.01, 0.1]},
        "Linear Regression": {},
        "XGBRegressor": {'n_estimators': [50, 100], 'learning_rate': [0.01, 0.1]},
        "CatBoosting Regressor": {'depth': [6, 8], 'learning_rate': [0.01, 0.1], 'iterations': [50, 100]},
        "AdaBoost Regressor": {'n_estimators': [50, 100], 'learning_rate': [0.01, 0.1]},
        "SVR": {'kernel': ['rbf', 'linear'], 'C': [0.1, 1, 10], 'epsilon': [0.01, 0.1]}
    }

    model_report, best_model, scaler = evaluate_models(X_train_scaled, y_train, X_test_scaled, y_test, models, params, stock_data, scaler)

    best_model_name_r2 = max(model_report, key=lambda x: model_report[x]['R²'])
    best_model_r2 = model_report[best_model_name_r2]['R²']
    best_model_mse = model_report[best_model_name_r2]['MSE']
    best_model_rmse = model_report[best_model_name_r2]['RMSE']
    best_model_nrmse = model_report[best_model_name_r2]['NRMSE (%)']
    print(f"\nBest Model (R²): {best_model_name_r2} with R² Score: {best_model_r2:.4f}, "
          f"MSE: {best_model_mse:.4f}, RMSE: {best_model_rmse:.4f}, NRMSE: {best_model_nrmse:.2f}%")

    best_model_name_nrmse = min(model_report, key=lambda x: model_report[x]['NRMSE (%)'])
    best_model_nrmse = model_report[best_model_name_nrmse]['NRMSE (%)']
    best_model_r2_nrmse = model_report[best_model_name_nrmse]['R²']
    best_model_mse_nrmse = model_report[best_model_name_nrmse]['MSE']
    best_model_rmse_nrmse = model_report[best_model_name_nrmse]['RMSE']
    print(f"Best Model (NRMSE): {best_model_name_nrmse} with R² Score: {best_model_r2_nrmse:.4f}, "
          f"MSE: {best_model_mse_nrmse:.4f}, RMSE: {best_model_rmse_nrmse:.4f}, NRMSE: {best_model_nrmse:.2f}%")
    
    return best_model, scaler