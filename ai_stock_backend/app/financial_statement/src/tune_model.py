# tune_models.py

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.metrics import accuracy_score
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
import joblib
import sys

# ─── Paths ─────────────────────────────────────────────────────────────
HERE        = Path(__file__).resolve().parent          # …/financial_statement/src
FIN_ROOT    = HERE.parent                              # …/financial_statement
PARQUET     = FIN_ROOT / "model_data.parquet"
BASE_MODEL  = FIN_ROOT / "models" / "stock_dir_model.pkl"
OUTPUT_DIR  = FIN_ROOT / "models"
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── 1) Load data & previously selected features ──────────────────────
if not PARQUET.exists():
    sys.exit(f"ERROR: {PARQUET} not found")
df = pd.read_parquet(PARQUET)

# Extract the feature list we already selected
base_art = joblib.load(BASE_MODEL)
features = base_art["features"]
print(f">> Tuning on {len(features)} features")

# Build growth frame (same as before)
raw_feats = [c[:-4] for c in features]  # strip "_chg"
df[raw_feats] = df[raw_feats].apply(pd.to_numeric, errors="coerce")
df = df.sort_values(["company_id","year"])
df_growth = (
    df
    .groupby("company_id")[raw_feats]
    .pct_change(fill_method=None)
    .add_suffix("_chg")
)

# X,y
X = df_growth[features].fillna(0)
y = (df["price_pct_change"] > 0).astype(int)

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# ─── 2) Logistic Regression grid ───────────────────────────────────────
print("\n>> Tuning LogisticRegression")
lr = LogisticRegression(max_iter=2000, random_state=42)
param_grid_lr = {
    "C": [0.01, 0.1, 1, 10, 100],
    "penalty": ["l1", "l2"],
    "solver": ["liblinear", "saga"]
}
gs_lr = GridSearchCV(
    lr,
    param_grid_lr,
    cv=cv,
    scoring="accuracy",
    n_jobs=-1,
    verbose=1
)
gs_lr.fit(X_train, y_train)
print(f"LR best score: {gs_lr.best_score_:.4f}, params: {gs_lr.best_params_}")

# Evaluate on hold-out
best_lr = gs_lr.best_estimator_
acc_lr  = accuracy_score(y_test, best_lr.predict(X_test))
print(f"LR test accuracy: {acc_lr:.4f}")

# ─── 3) XGBoost grid ───────────────────────────────────────────────────
print("\n>> Tuning XGBoost")
xgb = XGBClassifier(
    use_label_encoder=False,
    eval_metric="logloss",
    random_state=42
)
param_grid_xgb = {
    "n_estimators": [50, 100, 200],
    "max_depth": [3, 4, 6],
    "learning_rate": [0.01, 0.1, 0.2],
    "subsample": [0.6, 0.8, 1.0],
    "colsample_bytree": [0.6, 0.8, 1.0]
}
gs_xgb = GridSearchCV(
    xgb,
    param_grid_xgb,
    cv=cv,
    scoring="accuracy",
    n_jobs=-1,
    verbose=1
)
gs_xgb.fit(X_train, y_train)
print(f"XGB best score: {gs_xgb.best_score_:.4f}, params: {gs_xgb.best_params_}")

best_xgb = gs_xgb.best_estimator_
acc_xgb  = accuracy_score(y_test, best_xgb.predict(X_test))
print(f"XGB test accuracy: {acc_xgb:.4f}")

# ─── 4) Save the overall best model ────────────────────────────────────
if acc_xgb >= acc_lr:
    final_model, final_acc = best_xgb, acc_xgb
    name = "xgboost"
else:
    final_model, final_acc = best_lr, acc_lr
    name = "logreg"

out_path = OUTPUT_DIR / f"stock_dir_model_{name}_tuned.pkl"
joblib.dump({"model":final_model, "features":features}, out_path)
print(f"\n✅ Saved tuned {name!r} model ({final_acc:.4f}) to: {out_path}")
