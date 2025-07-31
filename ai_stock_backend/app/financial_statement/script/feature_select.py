import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path
import sys

def drop_redundant_features(df, threshold: float) -> set[str]:
    """
    Given a DataFrame df of numeric features, return the set of column names
    that should be dropped because they have |corr| > threshold with an earlier
    feature in the list.
    """
    corr_matrix = df.corr().abs()
    # Only look at the upper triangle
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    # Any column with a correlation above threshold to ANY earlier column gets dropped
    to_drop = {col for col in upper.columns if any(upper[col] > threshold)}
    return to_drop

# ─── 0) load data ────────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
PARQ = (HERE.parent / "model_data.parquet")
if not PARQ.exists():
    sys.exit(f"ERROR: cannot find {PARQ}")
df = pd.read_parquet(PARQ)

# ─── 1) identify IDs, target, raw features ──────────────────────────────
ID_COLS   = ["company_id", "year"]
TARGET    = "price_pct_change"
raw_feats = [c for c in df.columns if c not in ID_COLS + [TARGET]]

# ─── 2) coerce & sort ────────────────────────────────────────────────────
df[raw_feats] = df[raw_feats].apply(pd.to_numeric, errors="coerce")
df = df.sort_values(ID_COLS)

# ─── 3) compute YoY growth features ──────────────────────────────────────
df_growth = (
    df
    .groupby("company_id")[raw_feats]
    .pct_change(fill_method=None)
    .add_suffix("_chg")
)

# ─── 4) correlation vs. target (require ≥30 pairs) ───────────────────────
corrs = {}
min_pairs = 30
for col in df_growth.columns:
    s = df_growth[col]
    t = df[TARGET]
    valid = s.notna() & t.notna()
    if valid.sum() < min_pairs:
        continue
    corrs[col] = s[valid].corr(t[valid])

corr_s = pd.Series(corrs)
print(f">> {len(corr_s)} features had ≥{min_pairs} valid pairs for corr → target")

# ─── 5) filter by |corr| ≥ 0.25 ──────────────────────────────────────────
t_thresh = 0.15
cands    = corr_s[ corr_s.abs() >= t_thresh ] \
                      .sort_values(key=lambda s: s.abs(), ascending=False)
print(f">> {len(cands)} candidates with |r|≥{t_thresh}")

# ─── 6) drop redundant by inter‐corr > 0.75 ──────────────────────────────
f_thresh = 0.8
to_drop  = drop_redundant_features(df_growth[cands.index], f_thresh)
selected = [f for f in cands.index if f not in to_drop]
print(f">> Dropped {len(to_drop)} redundant features at |r|>{f_thresh}")
print(f">> {len(selected)} final features remain")

# ─── 7) show your features & heatmap ────────────────────────────────────
print("\nSelected features:")
for feat in selected:
    print(" •", feat)

top20 = selected[:20]
hm = pd.concat([df_growth[top20], df[TARGET]], axis=1)

plt.figure(figsize=(12,10))
sns.heatmap(
    hm.corr(),
    annot=True, fmt=".2f",
    cmap="vlag", center=0
)
plt.title(f"Top 20 Features (|r|≥{t_thresh}, inter‐feat corr≤{f_thresh})")
plt.tight_layout()
plt.show()
