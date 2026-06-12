"""All PG read/write functions for asset-monitor."""

import json
from pathlib import Path
from datetime import date, datetime

import asyncpg
import numpy as np
import pandas as pd

from app.db.pool import get_pool


# ── Schema init ────────────────────────────────────────────────

async def init_db():
    pool = get_pool()
    sql = (Path(__file__).parent / "schema.sql").read_text()
    async with pool.acquire() as conn:
        await conn.execute(sql)


# ── price_daily ────────────────────────────────────────────────

async def upsert_prices(rows: list[dict]):
    """Bulk upsert price rows. Each row: {ticker, trade_date, close, source}."""
    if not rows:
        return
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO price_daily (ticker, trade_date, close, source)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (ticker, trade_date) DO UPDATE SET
                   close = EXCLUDED.close,
                   source = EXCLUDED.source,
                   fetched_at = NOW()
            """,
            [(r["ticker"], r["trade_date"], r["close"], r.get("source")) for r in rows],
        )


async def load_prices(tickers: list[str] | None = None) -> pd.DataFrame:
    pool = get_pool()
    async with pool.acquire() as conn:
        if tickers:
            rows = await conn.fetch(
                "SELECT ticker, trade_date, close FROM price_daily WHERE ticker = ANY($1) ORDER BY trade_date",
                tickers,
            )
        else:
            rows = await conn.fetch("SELECT ticker, trade_date, close FROM price_daily ORDER BY trade_date")
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([dict(r) for r in rows])
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    pivot = df.pivot(index="trade_date", columns="ticker", values="close")
    return pivot.sort_index().astype(float)


async def get_latest_date(ticker: str) -> date | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT MAX(trade_date) AS d FROM price_daily WHERE ticker = $1", ticker
        )
    return row["d"] if row and row["d"] else None


async def get_ticker_count() -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(DISTINCT ticker) AS c FROM price_daily")
    return row["c"] if row else 0


# ── compute_cache ──────────────────────────────────────────────

async def save_compute(key: str, data_type: str, price_hash: str,
                       dates: list[str], values: list[float]):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO compute_cache (cache_key, data_type, price_hash, dates, values, row_count)
               VALUES ($1, $2, $3, $4, $5, $6)
               ON CONFLICT (cache_key) DO UPDATE SET
                   price_hash = EXCLUDED.price_hash,
                   dates = EXCLUDED.dates,
                   values = EXCLUDED.values,
                   row_count = EXCLUDED.row_count,
                   computed_at = NOW()
            """,
            key, data_type, price_hash,
            json.dumps(dates), json.dumps(values), len(values),
        )


async def load_compute(price_hash: str) -> dict[str, pd.Series]:
    """Load all cached computations matching price_hash. Returns {cache_key: Series}."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT cache_key, data_type, dates, values FROM compute_cache WHERE price_hash = $1",
            price_hash,
        )
    result = {}
    for row in rows:
        dates_raw = row["dates"]
        values_raw = row["values"]
        if isinstance(dates_raw, str):
            dates_raw = json.loads(dates_raw)
        if isinstance(values_raw, str):
            values_raw = json.loads(values_raw)
        dates = pd.to_datetime(dates_raw)
        values = np.array(values_raw)
        result[row["cache_key"]] = pd.Series(values, index=dates)
    return result


# ── signal_history ─────────────────────────────────────────────

async def save_signal(strategy_id: str, signal_date, holdings: list[dict], detail: dict | None):
    """signal_date accepts str ('YYYY-MM-DD') or date object."""
    pool = get_pool()
    if isinstance(signal_date, str):
        signal_date = date.fromisoformat(signal_date)
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO signal_history (strategy_id, signal_date, holdings, signal_detail)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (strategy_id, signal_date) DO UPDATE SET
                   holdings = EXCLUDED.holdings,
                   signal_detail = EXCLUDED.signal_detail,
                   captured_at = NOW()
            """,
            strategy_id, signal_date,
            json.dumps(holdings, ensure_ascii=False),
            json.dumps(detail, ensure_ascii=False) if detail else None,
        )


async def load_signal_history(strategy_id: str, limit: int = 30) -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT signal_date, holdings, signal_detail
               FROM signal_history
               WHERE strategy_id = $1
               ORDER BY signal_date DESC LIMIT $2""",
            strategy_id, limit,
        )
    return [dict(r) for r in rows]


# ── backtest_result ────────────────────────────────────────────

async def save_backtest(strategy_id: str, snapshot_date,
                        nav_curve: dict, metrics: dict | None = None,
                        data_hash: str | None = None):
    """snapshot_date accepts str ('YYYY-MM-DD') or date object."""
    pool = get_pool()
    if isinstance(snapshot_date, str):
        snapshot_date = date.fromisoformat(snapshot_date)
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO backtest_result (strategy_id, snapshot_date, nav_curve, metrics, data_hash)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (strategy_id, snapshot_date) DO UPDATE SET
                   nav_curve = EXCLUDED.nav_curve,
                   metrics = EXCLUDED.metrics,
                   data_hash = EXCLUDED.data_hash,
                   created_at = NOW()
            """,
            strategy_id, snapshot_date,
            json.dumps(nav_curve), json.dumps(metrics) if metrics else None,
            data_hash,
        )


async def load_backtest(strategy_id: str) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT nav_curve, metrics FROM backtest_result
               WHERE strategy_id = $1 ORDER BY snapshot_date DESC LIMIT 1""",
            strategy_id,
        )
    if not row:
        return None
    return {"nav_curve": row["nav_curve"], "metrics": row["metrics"]}
