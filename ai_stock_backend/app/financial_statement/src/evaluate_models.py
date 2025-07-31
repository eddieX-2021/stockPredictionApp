# evaluate_models.py
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
import xgboost as xgb
import joblib
import sys

def drop_redundant(df: pd.DataFrame, thresh: float) -> set:
    corrm = df.corr().abs()
    upper = corrm.where(np.triu(np.ones(corrm.shape), k=1).astype(bool))
    return {col for col in upper.columns if any(upper[col] > thresh)}

# ─── Paths ─────────────────────────────────────────────────────────────
HERE     = Path(__file__).resolve().parent      # …/financial_statement/src
DATA_PARQ= HERE.parent / "model_data.parquet"
if not DATA_PARQ.exists():
    sys.exit(f"ERROR: {DATA_PARQ} not found")

# ─── 1) Load & prepare features + target ──────────────────────────────
df = pd.read_parquet(DATA_PARQ)
ID_COLS   = ["company_id","year"]
TARGET    = "price_pct_change"
raw_feats = [c for c in df.columns if c not in ID_COLS + [TARGET]]

# numeric & sort
df[raw_feats] = df[raw_feats].apply(pd.to_numeric, errors="coerce")
df = df.sort_values(ID_COLS)

# YoY growth
df_growth = (
    df
    .groupby("company_id")[raw_feats]
    .pct_change(fill_method=None)
    .add_suffix("_chg")
)

# corr→target
corrs = {}
for col in df_growth.columns:
    s = df_growth[col]
    valid = s.notna() & df[TARGET].notna()
    if valid.sum() < 30:
        continue
    corrs[col] = s[valid].corr(df.loc[valid, TARGET])
corr_s = pd.Series(corrs)

# feature‐selection thresholds
t_thresh = 0.15   # keep moderate signals
f_thresh = 0.80   # drop high pairwise collinearity

cands   = corr_s[ corr_s.abs() >= t_thresh ] \
               .sort_values(key=lambda x: x.abs(), ascending=False)
to_drop = drop_redundant(df_growth[cands.index], f_thresh)
selected= [f for f in cands.index if f not in to_drop]

print(f">> Using {len(selected)} features (│r│≥{t_thresh}, inter-corr≤{f_thresh})")

# build X,y
X = df_growth[selected].fillna(0)
y = (df[TARGET] > 0).astype(int)

# train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# ─── 2) Define your models/pipelines ───────────────────────────────────
models = {
    "LogisticRegression": Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, random_state=42))
    ]),
    "LinearSVC": Pipeline([
        ("scale", StandardScaler()),
        ("clf", SVC(kernel="linear", probability=True, random_state=42))
    ]),
    "KNeighbors": Pipeline([
        ("scale", StandardScaler()),
        ("clf", KNeighborsClassifier())
    ]),
    "RandomForest": RandomForestClassifier(
        n_estimators=200, n_jobs=-1, random_state=42
    ),
    "XGBoost": xgb.XGBClassifier(
        n_estimators=100, use_label_encoder=False,
        eval_metric="logloss", random_state=42
    ),
    "MLP": Pipeline([
        ("scale", StandardScaler()),
        ("clf", MLPClassifier(
            hidden_layer_sizes=(100,50),
            max_iter=500,
            random_state=42
        ))
    ])
}

# ─── 3) Train & evaluate each ─────────────────────────────────────────
results = {}
for name, model in models.items():
    print(f"\n=== {name} ===")
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    acc   = accuracy_score(y_test, preds)
    print(f"Accuracy: {acc:.4f}")
    print(classification_report(y_test, preds, digits=4))
    results[name] = acc

# ─── 4) Summarize ─────────────────────────────────────────────────────
print("\nSummary of Test Accuracy:")
for name, acc in sorted(results.items(), key=lambda x: x[1], reverse=True):
    print(f" • {name:<15s}: {acc:.4f}")
