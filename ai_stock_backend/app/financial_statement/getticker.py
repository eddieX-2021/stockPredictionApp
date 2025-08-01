import os
import requests
import pandas as pd

# 1) SEC’s company tickers JSON
SEC_URL = "https://www.sec.gov/files/company_tickers.json"

# 2) Supply a proper User-Agent per SEC guidelines
HEADERS = {
    "User-Agent": "Eddie StockPredictionApp/1.0 (eddie@example.com)",
    "Accept-Encoding": "gzip, deflate"
}

# 3) Fetch the JSON
resp = requests.get(SEC_URL, headers=HEADERS, timeout=10)
resp.raise_for_status()  # will now succeed if headers are OK

# 4) Parse into a DataFrame
#    The JSON is a dict of { index: {cik_str, ticker, title}, … }
data = list(resp.json().values())
df_sec = (
    pd.DataFrame.from_records(data)
      .assign(company_id=lambda d: d["cik_str"].astype(int))
      .rename(columns={"ticker": "ticker", "title": "name_latest"})
      [["company_id", "ticker", "name_latest"]]
)

# 5) Ensure your ./data folder exists and save
os.makedirs("data", exist_ok=True)
df_sec.to_csv("data/sec_company_tickers.csv", index=False)

print(f"Fetched {len(df_sec):,} mappings from SEC")
