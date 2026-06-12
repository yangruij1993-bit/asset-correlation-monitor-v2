"""
Refresh A-share cache from tushare (fund_daily + fund_adj, forward-adjusted).
Pulls all A-share tickers defined in ALL_ASSETS and merges into cache/prices.csv.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd

from app.config.assets import ALL_ASSETS
from app.services.data_service_tushare import tushare_data_service

CACHE_FILE = Path(__file__).parent / "cache" / "prices.csv"

a_share_tickers = [t for t in ALL_ASSETS.keys() if t.endswith(".SH") or t.endswith(".SZ")]
print(f"A-share tickers to fetch: {len(a_share_tickers)}")

print("Fetching from tushare (fund_daily + fund_adj)...")
pivot = tushare_data_service.get_prices(a_share_tickers)
if pivot.empty:
    print("ERROR: No data from tushare")
    sys.exit(1)

print(f"Fetched {pivot.shape[0]} rows, {pivot.shape[1]} tickers")
print(f"Date range: {pivot.index[0].date()} -> {pivot.index[-1].date()}")
print(f"Non-null counts per ticker:")
print(pivot.notna().sum().to_string())

# Load existing cache
existing = pd.read_csv(CACHE_FILE, index_col=0, parse_dates=True)
print(f"\nExisting cache: {existing.shape}, date range {existing.index[0].date()} to {existing.index[-1].date()}")

# Merge: overwrite A-share columns with fresh tushare data (adds new dates too)
# combine_first on tushare side keeps non-A-share cols from existing, then we
# explicitly overwrite A-share columns with tushare values where present.
merged = existing.combine_first(pivot)
for col in pivot.columns:
    tushare_vals = pivot[col].dropna()
    if not tushare_vals.empty:
        merged[col] = tushare_vals.reindex(merged.index)

merged = merged.sort_index()
print(f"Merged cache: {merged.shape}")

a_cols = [c for c in merged.columns if c.endswith(".SH") or c.endswith(".SZ")]
u_cols = [c for c in merged.columns if c not in a_cols]
print(f"\nAfter merge:")
print(f"  US last date:        {merged[u_cols].last_valid_index().date()}")
print(f"  A-share last date:   {merged[a_cols].last_valid_index().date()}")

merged.to_csv(CACHE_FILE)
print(f"\nSaved to {CACHE_FILE}")
