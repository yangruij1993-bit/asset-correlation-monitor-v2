import pandas as pd
from pathlib import Path
from datetime import datetime
from app.config.assets import ASSET_GROUPS, TICKER_NAMES, ALL_ASSETS
from app.services.data_service_oracle import oracle_data_service, US_TICKER_TO_ORACLE
from app.services.data_service_tushare import tushare_data_service

import logging
logger = logging.getLogger(__name__)


def _is_a_share(ticker: str) -> bool:
    return ticker.endswith(".SH") or ticker.endswith(".SZ")


class DataService:
    def __init__(self, cache_dir: str = "../cache"):
        self.cache_dir = Path(__file__).parent.parent.parent / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.prices_file = self.cache_dir / "prices.csv"
        self.df: pd.DataFrame = None

    def _load_cache(self) -> pd.DataFrame:
        if self.prices_file.exists():
            return pd.read_csv(self.prices_file, index_col=0, parse_dates=True)
        return pd.DataFrame()

    def _save_cache(self, df: pd.DataFrame):
        df = df.sort_index().dropna(how='all')
        df.to_csv(self.prices_file)
        self.df = df
        logger.info(f"Cache saved. Shape: {df.shape}")

    # ── PG integration ──────────────────────────────────────────

    async def _load_from_pg(self) -> pd.DataFrame:
        """Load all prices from PG."""
        try:
            from app.db.repository import load_prices
            return await load_prices()
        except Exception as e:
            logger.warning(f"PG load_prices failed: {e}")
            return pd.DataFrame()

    async def _persist_to_pg(self, df: pd.DataFrame, source: str = "refresh"):
        """Persist DataFrame rows to PG price_daily (efficient stack-based)."""
        if df.empty:
            return
        try:
            from app.db.repository import upsert_prices
            stacked = df.stack()
            rows = []
            for (date_idx, ticker), val in stacked.items():
                dt = date_idx.date() if hasattr(date_idx, 'date') else pd.Timestamp(date_idx).date()
                rows.append({
                    "ticker": ticker,
                    "trade_date": dt,
                    "close": float(val),
                    "source": source,
                })
            if rows:
                batch_size = 5000
                for i in range(0, len(rows), batch_size):
                    await upsert_prices(rows[i:i + batch_size])
                logger.info(f"Persisted {len(rows)} rows to PG ({source})")
        except Exception as e:
            logger.warning(f"PG persist failed: {e}")

    # ── Data loading (PG primary, CSV fallback) ────────────────

    async def ensure_data(self):
        """Load price data: PG (primary) → CSV (fallback) → refresh."""
        # 1. Try PG
        pg_df = await self._load_from_pg()
        if not pg_df.empty:
            self.df = pg_df
            print(f"Loaded prices from PG: {pg_df.shape[1]} tickers, {pg_df.shape[0]} dates, latest={pg_df.index[-1].date()}")
            # Ensure CSV exists for hash compatibility
            if not self.prices_file.exists():
                self._save_cache(pg_df)
            # Check staleness
            last_date = pd.to_datetime(pg_df.index[-1]).date()
            today = datetime.now().date()
            if (today - last_date).days > 3:
                logger.info("PG data stale, refreshing...")
                new_data = self.refresh_data()
                if not new_data.empty:
                    await self._persist_to_pg(new_data, source="refresh")
            return

        # 2. Try CSV + migrate to PG
        csv_df = self._load_cache()
        if not csv_df.empty:
            self.df = csv_df
            logger.info(f"Loaded prices from CSV: {csv_df.shape}, migrating to PG...")
            await self._persist_to_pg(csv_df, source="csv_migration")
            return

        # 3. Fresh fetch
        new_data = self.refresh_data()
        if not new_data.empty:
            await self._persist_to_pg(new_data, source="initial_fetch")

    def refresh_data(self) -> pd.DataFrame:
        """Refresh data: fetch from sources and MERGE into existing cache.
        Returns newly fetched data (for PG persist)."""
        all_tickers = list(ALL_ASSETS.keys())
        a_share_tickers = [t for t in all_tickers if _is_a_share(t)]
        us_tickers = [t for t in all_tickers if not _is_a_share(t)]

        us_oracle_tickers = [t for t in us_tickers if t in US_TICKER_TO_ORACLE]
        us_yfinance_tickers = [t for t in us_tickers if t not in US_TICKER_TO_ORACLE]

        # Start from existing cache so we never lose data on partial failure
        base = self._load_cache() if self.prices_file.exists() else pd.DataFrame()
        new_data = pd.DataFrame()

        # 1. A-share data from tushare (fresh; Oracle CHINACLOSEDFUNDEODPRICE is stale)
        if a_share_tickers:
            logger.info(f"Fetching {len(a_share_tickers)} A-share tickers from tushare...")
            a_prices = tushare_data_service.get_prices(a_share_tickers)
            if not a_prices.empty:
                new_data = pd.concat([new_data, a_prices], axis=1)
            else:
                logger.warning("tushare A-share fetch failed, A-share data not updated")

        # 2. US ETFs from Oracle (WK_GLOBAL_STOCKS), fallback to yfinance
        if us_oracle_tickers:
            logger.info(f"Fetching {len(us_oracle_tickers)} US tickers from Oracle...")
            us_prices = oracle_data_service.get_us_prices(us_oracle_tickers)
            if not us_prices.empty:
                new_data = pd.concat([new_data, us_prices], axis=1)
                fetched = set(us_prices.columns)
                oracle_missing = [t for t in us_oracle_tickers if t not in fetched]
            else:
                oracle_missing = us_oracle_tickers

            if oracle_missing:
                logger.info(f"Oracle missing {len(oracle_missing)} tickers, trying yfinance: {oracle_missing}")
                yf_prices = self._fetch_yfinance(oracle_missing)
                if not yf_prices.empty:
                    new_data = pd.concat([new_data, yf_prices], axis=1)

        # 3. Remaining US tickers from yfinance
        if us_yfinance_tickers:
            logger.info(f"Fetching {len(us_yfinance_tickers)} US tickers from yfinance...")
            yf_prices = self._fetch_yfinance(us_yfinance_tickers)
            if not yf_prices.empty:
                new_data = pd.concat([new_data, yf_prices], axis=1)

        # Merge: update existing cache with new data, never lose old columns
        if base.empty:
            base = new_data
        elif not new_data.empty:
            for col in new_data.columns:
                base[col] = new_data[col]
        self._save_cache(base)
        return new_data

    def _fetch_yfinance(self, tickers: list[str]) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance not installed.")
            return pd.DataFrame()

        try:
            data = yf.download(tickers, period="max", auto_adjust=True, progress=False)
            if len(tickers) == 1:
                close = data["Close"].to_frame(name=tickers[0])
            else:
                close = data["Close"]
            close.columns = [str(c) for c in close.columns]
        except Exception as e:
            logger.warning(f"yfinance batch download failed: {e}")
            close = pd.DataFrame()

        fetched = set(close.columns) if not close.empty else set()
        missing = [t for t in tickers if t not in fetched or (not close.empty and close[t].dropna().empty)]
        for t in missing:
            try:
                hist = yf.Ticker(t).history(period="max", auto_adjust=True)
                if hist.empty:
                    logger.warning(f"yfinance: {t} no data")
                    continue
                series = hist["Close"].rename(t)
                series.index = series.index.tz_localize(None)
                if not close.empty and t in close.columns:
                    close = close.drop(columns=[t])
                if close.empty:
                    close = series.to_frame()
                else:
                    close = close.join(series, how='outer')
                logger.info(f"yfinance fallback: {t} OK ({len(hist)} rows)")
            except Exception as e:
                logger.warning(f"yfinance: {t} failed: {e}")

        if close.empty:
            return pd.DataFrame()
        return close.dropna(how='all')

    def load_data(self) -> pd.DataFrame:
        if self.df is None:
            self.df = self._load_cache()
            if self.df.empty:
                self.refresh_data()
        return self.df

    def get_last_date(self) -> str:
        if self.df is not None and not self.df.empty:
            return str(self.df.index[-1].date())
        return "N/A"

    def get_tickers_for_group(self, group: str) -> list:
        return ASSET_GROUPS.get(group, list(ALL_ASSETS.keys()))

    def get_ticker_name(self, ticker: str) -> str:
        return TICKER_NAMES.get(ticker, ticker)


data_service = DataService()
