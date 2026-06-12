"""
Doris data service for US ETF/Index daily prices.
Uses extended_us_market_fmp (historical) + extended_us_market_daily (recent).
"""

import os
import logging
from typing import Optional

import pymysql
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DorisDataService:
    """Fetches US ETF/index daily close prices from Doris."""

    def __init__(self):
        self.host = os.getenv("DORIS_HOST", "")
        self.port = int(os.getenv("DORIS_PORT", "9030"))
        self.user = os.getenv("DORIS_USER", "")
        self.password = os.getenv("DORIS_PASSWORD", "")
        self.database = os.getenv("DORIS_DATABASE", "dev_db")

    def get_prices(
        self,
        tickers: list[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch daily adjusted close prices for US tickers from Doris.

        Args:
            tickers: e.g. ["VOO", "QQQ", "XLF"]
            start_date: YYYY-MM-DD (default: 5 years ago)
            end_date: YYYY-MM-DD (default: today)

        Returns:
            DataFrame with DatetimeIndex, columns = tickers, values = adj_close
        """
        if not all([self.host, self.user, self.password, self.database]):
            logger.warning("Doris credentials not configured")
            return pd.DataFrame()

        if start_date is None:
            start_date = (pd.Timestamp.now() - pd.DateOffset(years=5)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = pd.Timestamp.now().strftime("%Y-%m-%d")

        try:
            conn = pymysql.connect(
                host=self.host, port=self.port,
                user=self.user, password=self.password,
                database=self.database,
            )
            try:
                ticker_list = ", ".join(f"'{t}'" for t in tickers)

                # Historical data from fmp table (adj_close available)
                sql_fmp = f"""
                    SELECT fmp_ticker AS ticker, trade_dt AS trade_date, adj_close
                    FROM extended_us_market_fmp
                    WHERE fmp_ticker IN ({ticker_list})
                      AND trade_dt >= %s AND trade_dt <= %s
                """
                df_fmp = pd.read_sql(sql_fmp, conn, params=[start_date, end_date])

                # Recent data from daily table (close as adj_close)
                sql_daily = f"""
                    SELECT poly_ticker AS ticker, trade_dt AS trade_date, close_price AS adj_close
                    FROM extended_us_market_daily
                    WHERE poly_ticker IN ({ticker_list})
                      AND trade_dt >= %s AND trade_dt <= %s
                """
                df_daily = pd.read_sql(sql_daily, conn, params=[start_date, end_date])

                df = pd.concat([df_fmp, df_daily], ignore_index=True)
                if df.empty:
                    return pd.DataFrame()

                df["trade_date"] = pd.to_datetime(df["trade_date"])
                df["adj_close"] = pd.to_numeric(df["adj_close"], errors="coerce")
                df = df.sort_values(["ticker", "trade_date"])
                df = df.drop_duplicates(subset=["ticker", "trade_date"], keep="first")

                pivot = df.pivot(index="trade_date", columns="ticker", values="adj_close")
                pivot = pivot.sort_index()
                for t in tickers:
                    if t not in pivot.columns:
                        pivot[t] = float("nan")
                return pivot[tickers].astype(float)
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Doris query failed: {e}")
            return pd.DataFrame()


doris_data_service = DorisDataService()
