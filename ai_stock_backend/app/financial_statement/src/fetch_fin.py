# fetch_fin.py
import yfinance as yf

def fetch_financials(ticker: str) -> dict[str, dict]:
    """
    Fetch the last two years of annual income statement, balance sheet,
    and cash-flow from Yahoo Finance via yfinance.
    Returns {"latest": {...}, "prev": {...}} where each dict maps
    metric name -> value.
    """
    tk = yf.Ticker(ticker.upper())

    # yfinance returns DataFrames with columns = period (Timestamp) descending
    inc = tk.financials        # annual income statement
    bal = tk.balance_sheet     # annual balance sheet
    cash = tk.cashflow         # annual cash flow

    # Ensure we have at least two periods
    if inc.shape[1] < 2 or bal.shape[1] < 2 or cash.shape[1] < 2:
        raise ValueError(f"Not enough annual periods for {ticker}")

    # The first column is the most recent period, second is prior year
    periods = [inc.columns[0], inc.columns[1]]

    latest = {}
    prev   = {}

    # Helper to merge one DataFrame's columns into dicts
    def merge_df(df, period, target_dict):
        col = df[period]
        for metric, val in col.items():
            target_dict[metric] = float(val) if not pd.isna(val) else None

    import pandas as pd
    for period, dest in zip(periods, (latest, prev)):
        merge_df(inc,  period, dest)
        merge_df(bal,  period, dest)
        merge_df(cash, period, dest)

    return {"latest": latest, "prev": prev}
