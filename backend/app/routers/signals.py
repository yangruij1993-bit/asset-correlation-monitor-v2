import asyncio
import hashlib
import json
import os
from datetime import date, datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List

from app.models.signal_schema import SignalOverview, SignalDetail, NavCurve, BacktestMetrics, SignalHistoryItem
from app.services.generic_signal_parser import generic_signal_parser

router = APIRouter(prefix="/api/v1/signals", tags=["Strategy Signals"])


def _get_overview(strategy_id: str) -> SignalOverview | None:
    return generic_signal_parser.get_overview(strategy_id)


def _get_overviews() -> list[SignalOverview]:
    return generic_signal_parser.get_overviews()


def _get_detail(strategy_id: str) -> SignalDetail | None:
    return generic_signal_parser.get_detail(strategy_id)


def _get_history(strategy_id: str, limit: int = 30) -> list[SignalHistoryItem]:
    return generic_signal_parser.get_history(strategy_id, limit)


async def _save_signal_snapshot(overview: SignalOverview):
    try:
        from app.db.repository import save_signal
        holdings = [h.model_dump() for h in overview.holdings]
        await save_signal(
            strategy_id=overview.strategy_id,
            signal_date=overview.signal_date,
            holdings=holdings,
            detail=overview.signal_detail,
        )
    except Exception:
        pass


async def _save_nav_cache(strategy_id: str, curve: NavCurve, metrics: BacktestMetrics | None):
    try:
        from app.db.repository import save_backtest
        nav_data = {"dates": curve.dates, "nav": curve.nav}
        if curve.benchmark_nav:
            nav_data["benchmark_nav"] = curve.benchmark_nav
        metrics_data = metrics.model_dump() if metrics else None
        data_hash = hashlib.md5(json.dumps(nav_data).encode()).hexdigest()[:16]
        await save_backtest(
            strategy_id=strategy_id,
            snapshot_date=str(date.today()),
            nav_curve=nav_data,
            metrics=metrics_data,
            data_hash=data_hash,
        )
    except Exception:
        pass


async def _load_nav_cache(strategy_id: str) -> dict | None:
    try:
        from app.db.repository import load_backtest
        return await load_backtest(strategy_id)
    except Exception:
        return None


@router.get("/overview", response_model=List[SignalOverview])
async def get_all_overviews():
    overviews = _get_overviews()
    await asyncio.gather(*[_save_signal_snapshot(ov) for ov in overviews], return_exceptions=True)
    return overviews


@router.get("/overview/{strategy_id}", response_model=SignalOverview)
async def get_overview(strategy_id: str):
    result = _get_overview(strategy_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    await _save_signal_snapshot(result)
    return result


@router.get("/detail/{strategy_id}", response_model=SignalDetail)
async def get_detail(strategy_id: str):
    result = _get_detail(strategy_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    return result


@router.get("/nav/{strategy_id}", response_model=NavCurve)
async def get_nav(strategy_id: str):
    # 1. PG cache
    cached = await _load_nav_cache(strategy_id)
    if cached and cached.get("nav_curve"):
        nc = cached["nav_curve"]
        if isinstance(nc, str):
            nc = json.loads(nc)
        return NavCurve(
            strategy_id=strategy_id,
            dates=nc.get("dates", []),
            nav=nc.get("nav", []),
            benchmark_nav=nc.get("benchmark_nav"),
        )

    # 2. Generic parser
    result = generic_signal_parser.get_nav(strategy_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"NAV data not found for {strategy_id}")

    metrics = None
    try:
        detail = generic_signal_parser.get_detail(strategy_id)
        if detail and detail.metrics:
            metrics = detail.metrics
    except Exception:
        pass
    await _save_nav_cache(strategy_id, result, metrics)
    return result


@router.get("/metrics/{strategy_id}", response_model=BacktestMetrics)
async def get_metrics(strategy_id: str):
    # PG cache
    cached = await _load_nav_cache(strategy_id)
    if cached and cached.get("metrics"):
        m = cached["metrics"]
        if isinstance(m, str):
            m = json.loads(m)
        return BacktestMetrics(**m)

    # Generic parser
    detail = generic_signal_parser.get_detail(strategy_id)
    if detail and detail.metrics:
        return detail.metrics

    raise HTTPException(status_code=404, detail=f"Metrics not available for {strategy_id}")


@router.get("/history/{strategy_id}", response_model=List[SignalHistoryItem])
async def get_history(strategy_id: str, limit: int = 30):
    # PG first
    try:
        from app.db.repository import load_signal_history
        rows = await load_signal_history(strategy_id, limit)
        if rows:
            items = []
            for row in rows:
                sd = row["signal_date"]
                holdings = row["holdings"]
                detail = row.get("signal_detail") or {}
                if isinstance(sd, date):
                    sd = str(sd)
                if isinstance(holdings, str):
                    holdings = json.loads(holdings)
                if isinstance(detail, str):
                    detail = json.loads(detail)
                items.append(SignalHistoryItem(
                    date=sd,
                    action=detail.get("action", "hold"),
                    detail={"holdings": holdings, **detail},
                ))
            return items
    except Exception:
        pass

    return _get_history(strategy_id, limit)
