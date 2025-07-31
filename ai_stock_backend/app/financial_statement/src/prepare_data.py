import os
import pandas as pd
import requests
import yfinance as yf
from tqdm import tqdm

HERE      = os.path.dirname(os.path.abspath(__file__))
BASE      = os.path.normpath(os.path.join(HERE, ".."))        
DATA_DIR  = os.path.join(BASE, "data")
COMP_CSV  = os.path.join(DATA_DIR, "companies.csv")
FUND_CSV  = os.path.join(DATA_DIR, "fundamental.csv")           
OUT_FILE  = os.path.join(BASE, "model_data.parquet")


def find_ticker(name: str) -> str | None:
    """
    Query Yahoo Finance suggestion API for 'name' and return the first symbol.
    """
    try:
        resp = requests.get(
            "https://query1.finance.yahoo.com/v1/finance/search",
            params={"q": name},
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        quotes = data.get("quotes", [])
        if not quotes:
            return None
        return quotes[0].get("symbol")
    except Exception:
        return None

companies = pd.read_csv(COMP_CSV)
funds     = pd.read_csv(FUND_CSV)


year_cols = [str(y) for y in range(2010, 2017)]
funds_long = (
    funds
    .melt(
        id_vars=["company_id", "indicator_id"],
        value_vars=year_cols,
        var_name="year",
        value_name="value"
    )
    .dropna(subset=["value"])
)

df_feat = (
    funds_long
    .pivot_table(
        index=["company_id", "year"],
        columns="indicator_id",
        values="value"
    )
    .reset_index()
)


price_changes = []
seen_tickers   = {} 

for cid, group in tqdm(df_feat.groupby("company_id"), desc="Companies"):
    if cid in seen_tickers:
        ticker = seen_tickers[cid]
    else:
        name = companies.loc[companies.company_id == cid, "name_latest"]
        if name.empty:
            ticker = None
        else:
            ticker = find_ticker(name.iat[0])
        seen_tickers[cid] = ticker

    if not ticker:
        continue

    hist = yf.Ticker(ticker).history(
        start="2009-12-01",
        end="2018-01-10",
        auto_adjust=False
    )
    if hist.empty:
        continue

    hist["year"] = hist.index.year
    year_end = hist.groupby("year")["Close"].last()

    
    for y in range(2010, 2016):
        if y in year_end.index and (y + 1) in year_end.index:
            pct = (year_end[y + 1] - year_end[y]) / year_end[y]
            price_changes.append({
                "company_id": cid,
                "year":       str(y),
                "price_pct_change": pct
            })

df_price = pd.DataFrame(price_changes, columns=["company_id","year","price_pct_change"])

df = df_feat.merge(
     df_price,
     on=["company_id", "year"],
     how="inner"
)

df.to_parquet(OUT_FILE, index=False)
print(f"✅ Saved prepared data to {OUT_FILE}")
