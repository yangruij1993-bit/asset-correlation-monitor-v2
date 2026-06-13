"""
Oracle data service for A-share and US ETF/Index daily prices.
A-shares: WKWD_SYNC.CHINACLOSEDFUNDEODPRICE
US ETFs:  WKWD_SYNC.WK_GLOBAL_STOCKS
"""

import os
import logging
from typing import Optional

import oracledb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_ORACLE_CLIENT_DIR = os.getenv(
    "ORACLE_CLIENT_DIR",
    "/opt/homebrew/Cellar/instantclient-arm64-basic/23.3.0.23.09-1/lib",
)
_ORACLE_SCHEMA = os.getenv("ORACLE_SCHEMA", "WKWD_SYNC")
_oracle_initialized = False

# Mapping from yfinance-style tickers to Oracle WIND_CODE in WK_GLOBAL_STOCKS
US_TICKER_TO_ORACLE = {
    "QQQ": "QQQ.O",
    "USMV": "USMV.BAT",
    "SPMO": "SPMO.P",
    "XLF": "XLF.P",
    "XLE": "XLE.P",
    "XLK": "XLK.P",
    "XLY": "XLY.P",
    "XLP": "XLP.P",
    "XLV": "XLV.P",
    "XLU": "XLU.P",
    "XLB": "XLB.P",
    "XLI": "XLI.P",
    "XLRE": "XLRE.P",
    "XLC": "XLC.P",
    "TLT": "TLT.O",
    "GLD": "GLD.P",
}


def _init_client():
    global _oracle_initialized
    if not _oracle_initialized:
        try:
            oracledb.init_oracle_client(lib_dir=_ORACLE_CLIENT_DIR)
        except Exception:
            pass
        _oracle_initialized = True


class OracleDataService:
    """Fetches A-share and US ETF/index daily close prices from Oracle (Wind schema)."""

    def __init__(self):
        self.user = os.getenv("ORACLE_USER", "")
        self.password = os.getenv("ORACLE_PASSWORD", "")
        self.dsn = os.getenv("ORACLE_DSN", "")

    def get_prices(
        self,
        tickers: list[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch A-share ETF prices from CHINACLOSEDFUNDEODPRICE."""
        if not all([self.user, self.password, self.dsn]):
            logger.warning("Oracle credentials not configured")
            return pd.DataFrame()

        _init_client()

        params = {}
        date_filter = ""
        if start_date is not None:
            date_filter += " AND TRADE_DT >= :start_date"
            params["start_date"] = start_date
        if end_date is not None:
            date_filter += " AND TRADE_DT <= :end_date"
            params["end_date"] = end_date

        try:
            conn = oracledb.connect(user=self.user, password=self.password, dsn=self.dsn)
            try:
                ticker_list = ", ".join(f"'{t}'" for t in tickers)
                sql = f"""
                    SELECT S_INFO_WINDCODE AS ticker, TRADE_DT AS trade_date, S_DQ_ADJCLOSE AS adj_close
                    FROM {_ORACLE_SCHEMA}.CHINACLOSEDFUNDEODPRICE
                    WHERE S_INFO_WINDCODE IN ({ticker_list})
                    {date_filter}
                    ORDER BY TRADE_DT, S_INFO_WINDCODE
                """
                df = pd.read_sql(sql, conn, params=params)
                if df.empty:
                    return pd.DataFrame()

                df["TRADE_DATE"] = pd.to_datetime(df["TRADE_DATE"], format="%Y%m%d")
                pivot = df.pivot(index="TRADE_DATE", columns="TICKER", values="ADJ_CLOSE")
                pivot = pivot.sort_index()
                for t in tickers:
                    if t not in pivot.columns:
                        pivot[t] = float("nan")
                return pivot[tickers].astype(float)
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Oracle A-share query failed: {e}")
            return pd.DataFrame()

    def get_us_prices(
        self,
        tickers: list[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch US ETF prices from WK_GLOBAL_STOCKS. Returns empty for tickers not in Oracle."""
        oracle_tickers = {t: US_TICKER_TO_ORACLE[t] for t in tickers if t in US_TICKER_TO_ORACLE}
        if not oracle_tickers:
            return pd.DataFrame()

        _init_client()

        params = {}
        date_filter = ""
        if start_date is not None:
            date_filter += " AND TRADE_DT >= :start_date"
            params["start_date"] = start_date
        if end_date is not None:
            date_filter += " AND TRADE_DT <= :end_date"
            params["end_date"] = end_date

        try:
            conn = oracledb.connect(user=self.user, password=self.password, dsn=self.dsn)
            try:
                oracle_codes = list(oracle_tickers.values())
                ticker_list = ", ".join(f"'{t}'" for t in oracle_codes)
                sql = f"""
                    SELECT WIND_CODE AS ticker, TRADE_DT AS trade_date, S_DQ_CLOSE AS adj_close
                    FROM {_ORACLE_SCHEMA}.WK_GLOBAL_STOCKS
                    WHERE WIND_CODE IN ({ticker_list})
                    {date_filter}
                    ORDER BY TRADE_DT, WIND_CODE
                """
                df = pd.read_sql(sql, conn, params=params)
                if df.empty:
                    return pd.DataFrame()

                # Map Oracle WIND_CODE back to yfinance tickers
                reverse_map = {v: k for k, v in oracle_tickers.items()}
                df["TICKER"] = df["TICKER"].map(reverse_map)
                df = df.dropna(subset=["TICKER"])

                df["TRADE_DATE"] = pd.to_datetime(df["TRADE_DATE"], format="%Y%m%d")
                df["ADJ_CLOSE"] = pd.to_numeric(df["ADJ_CLOSE"], errors="coerce")
                pivot = df.pivot(index="TRADE_DATE", columns="TICKER", values="ADJ_CLOSE")
                pivot = pivot.sort_index()
                yf_tickers = list(oracle_tickers.keys())
                for t in yf_tickers:
                    if t not in pivot.columns:
                        pivot[t] = float("nan")
                return pivot[yf_tickers].astype(float)
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Oracle US ETF query failed: {e}")
            return pd.DataFrame()


oracle_data_service = OracleDataService()
