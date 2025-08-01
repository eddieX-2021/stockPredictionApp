import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from xgboost import XGBClassifier
import joblib
from pathlib import Path
import sys

def drop_redundant(df: pd.DataFrame, thresh: float) -> set:
    corrm = df.corr().abs()
    upper = corrm.where(np.triu(np.ones(corrm.shape), k=1).astype(bool))
    return {col for col in upper.columns if any(upper[col] > thresh)}

# ─── Paths ─────────────────────────────────────────────────────────────
HERE      = Path(__file__).resolve().parent              # …/financial_statement/src
FIN_ROOT  = HERE.parent                                  # …/financial_statement
PARQ      = FIN_ROOT / "model_data.parquet"
MODEL_OUT = FIN_ROOT / "models" / "stock_dir_model.pkl"

if not PARQ.exists():
    sys.exit(f"ERROR: {PARQ} not found")
MODEL_OUT.parent.mkdir(exist_ok=True)

# ─── 1) Load & prep raw fundamentals + target ──────────────────────────
df = pd.read_parquet(PARQ)
ID_COLS   = ["company_id", "year"]
TARGET    = "price_pct_change"
raw_feats = [c for c in df.columns if c not in ID_COLS + [TARGET]]

# coerce to numeric & sort
df[raw_feats] = df[raw_feats].apply(pd.to_numeric, errors="coerce")
df = df.sort_values(ID_COLS)

# ─── 2) Compute YoY pct-change features ────────────────────────────────
df_growth = (
    df
    .groupby("company_id")[raw_feats]
    .pct_change(fill_method=None)
    .add_suffix("_chg")
)

# ─── 3) Correlation vs. target (≥30 valid pairs) ───────────────────────
corrs = {}
for col in df_growth.columns:
    s = df_growth[col]
    valid = s.notna() & df[TARGET].notna()
    if valid.sum() < 30:
        continue
    corrs[col] = s[valid].corr(df.loc[valid, TARGET])
corr_s = pd.Series(corrs)
print(f">> {len(corr_s)} features passed the ≥30-pair filter")

# ─── 4) Keep features with |corr| ≥ 0.25 ───────────────────────────────
t_thresh = 0.15
cands    = corr_s[ corr_s.abs() >= t_thresh ] \
                  .sort_values(key=lambda s: s.abs(), ascending=False)
print(f">> {len(cands)} candidates with |r|≥{t_thresh}")

# ─── 5) Drop inter-feature corr > 0.75 ────────────────────────────────
f_thresh = 0.8
to_drop  = drop_redundant(df_growth[cands.index], f_thresh)
selected = [f for f in cands.index if f not in to_drop]
print(f">> {len(selected)} final features (dropped {len(to_drop)} redundant)")

# ─── 6) Build X,y – fill missing growth with 0 so we keep all rows ─────
X = df_growth[selected].fillna(0)
y = (df[TARGET] > 0).astype(int)

# sanity check
if X.empty or len(y)==0:
    sys.exit("ERROR: no samples to train on after filling NaNs")

# ─── 7) Train/test split & fit ────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)
model = XGBClassifier(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=4,
    random_state=42,
    use_label_encoder=False,
    eval_metric="logloss"
)
model.fit(X_train, y_train)

# ─── 8) Evaluate & save ───────────────────────────────────────────────
print(classification_report(y_test, model.predict(X_test)))
joblib.dump({"model":model, "features":selected}, MODEL_OUT)
print(f"✅ Model + features saved to {MODEL_OUT}")
