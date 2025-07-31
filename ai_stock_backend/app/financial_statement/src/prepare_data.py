import os
import pandas as pd
import yfinance as yf
from tqdm import tqdm

# ─── PATH SETUP ───────────────────────────────────────────────
HERE     = os.path.dirname(__file__)
BASE     = os.path.normpath(os.path.join(HERE, ".."))
DATA_DIR = os.path.join(BASE, "data")

# ─── LOAD FUNDAMENTALS ────────────────────────────────────────
funds = pd.read_csv(os.path.join(DATA_DIR, "fundamental.csv"), dtype={"company_id": str})

# identify all year-columns (e.g. "2010","2011",…)
year_cols = [c for c in funds.columns if c.isdigit()]

# ─── MELT into long form ──────────────────────────────────────
funds_long = (
    funds
      .melt(
          id_vars=["company_id", "indicator_id"],
          value_vars=year_cols,
          var_name="year",
          value_name="value",
      )
      .dropna(subset=["value"])           # drop missing
)

# ─── PIVOT so each indicator_id is a column ─────────────────
df_feat = (
    funds_long
      .pivot(index=["company_id", "year"], columns="indicator_id", values="value")
      .reset_index()
)
df_feat.columns.name = None  # tidy up

# ─── JOIN TICKERS ─────────────────────────────────────────────
sec_map = pd.read_csv(os.path.join(DATA_DIR, "sec_company_tickers.csv"), dtype={"company_id": str})
df_feat = df_feat.merge(sec_map, on="company_id", how="left")

# ─── FETCH YEAR-OVER-YEAR PRICE CHANGES ───────────────────────
price_changes = []
for _, row in tqdm(df_feat.iterrows(), total=len(df_feat)):
    cid    = row.company_id
    ticker = row.ticker
    year   = int(row.year)

    if pd.isna(ticker):
        continue

    hist = yf.Ticker(ticker).history(
        start=f"{year}-01-01",
        end=f"{year+1}-01-31",
        auto_adjust=False
    )
    if hist.empty:
        continue

    # last closing price of each calendar year
    year_end = hist.groupby(hist.index.year)["Close"].last()
    if year   in year_end.index and (year+1) in year_end.index:
        pct = (year_end[year+1] - year_end[year]) / year_end[year]
        price_changes.append({
            "company_id":       cid,
            "year":             str(year),
            "price_pct_change": pct
        })

df_price = pd.DataFrame(price_changes)

# ─── FINAL MERGE & SAVE ───────────────────────────────────────
df_final = df_feat.merge(df_price, on=["company_id", "year"], how="inner")
df_final.to_parquet(os.path.join(BASE, "model_data.parquet"), index=False)

print(f"✅ model_data.parquet ready: {df_final.shape[0]} rows")
