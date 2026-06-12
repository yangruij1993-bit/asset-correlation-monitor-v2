import asyncio
import hashlib
import json
from datetime import date, datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List

from app.models.signal_schema import SignalOverview, SignalDetail, NavCurve, BacktestMetrics, SignalHistoryItem
from app.services.signal_parser import signal_parser
from app.services.nav_builder import nav_builder, async_build_macro_6cycle_nav
from app.services.strategy_scheduler import (
    run_csi500_timing, run_macro_6cycle, run_sharpe_rotation,
    run_us_fusion, run_weekend_arb, get_scheduler_status, _run_log,
)

router = APIRouter(prefix="/api/v1/signals", tags=["Strategy Signals"])

STRATEGY_IDS = [
    "macro-6cycle", "sharpe-rotation", "weekend-arb",
    "csi500-timing", "us-fusion", "cn-us-hk-timing",
    "spmo-usmv-64",
]


async def _save_signal_snapshot(overview: SignalOverview):
    """Persist today's signal to PG (fire-and-forget)."""
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
    """Persist NAV curve + metrics to PG."""
    try:
        from app.db.repository import save_backtest
        nav_data = {"dates": curve.dates, "nav": curve.nav}
        if curve.benchmark_nav:
            nav_data["benchmark_nav"] = curve.benchmark_nav
        metrics_data = metrics.model_dump() if metrics else None
        # Hash the nav data for cache invalidation
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
    """Load cached NAV from PG."""
    try:
        from app.db.repository import load_backtest
        return await load_backtest(strategy_id)
    except Exception:
        return None


@router.get("/overview", response_model=List[SignalOverview])
async def get_all_overviews():
    overviews = signal_parser.get_overviews()
    # Auto-save all snapshots concurrently
    await asyncio.gather(*[_save_signal_snapshot(ov) for ov in overviews], return_exceptions=True)
    return overviews


@router.get("/overview/{strategy_id}", response_model=SignalOverview)
async def get_overview(strategy_id: str):
    if strategy_id not in STRATEGY_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy_id}")
    result = signal_parser.get_overview(strategy_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    await _save_signal_snapshot(result)
    return result


@router.get("/detail/{strategy_id}", response_model=SignalDetail)
async def get_detail(strategy_id: str):
    if strategy_id not in STRATEGY_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy_id}")
    result = signal_parser.get_detail(strategy_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    return result


@router.get("/nav/{strategy_id}", response_model=NavCurve)
async def get_nav(strategy_id: str):
    if strategy_id not in STRATEGY_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy_id}")

    # 1. Try PG cache first
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

    # 2. Compute from files
    if strategy_id == "macro-6cycle":
        result = await async_build_macro_6cycle_nav()
    else:
        result = nav_builder.get_nav(strategy_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"NAV data not found for {strategy_id}")

    # 3. Cache to PG
    metrics = nav_builder.compute_metrics(strategy_id)
    await _save_nav_cache(strategy_id, result, metrics)
    return result


@router.get("/metrics/{strategy_id}", response_model=BacktestMetrics)
async def get_metrics(strategy_id: str):
    if strategy_id not in STRATEGY_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy_id}")

    # Try PG cache
    cached = await _load_nav_cache(strategy_id)
    if cached and cached.get("metrics"):
        m = cached["metrics"]
        if isinstance(m, str):
            m = json.loads(m)
        return BacktestMetrics(**m)

    # Compute
    if strategy_id == "macro-6cycle":
        curve = await async_build_macro_6cycle_nav()
        if curve and len(curve.nav) >= 10:
            result = nav_builder.compute_metrics("macro-6cycle")
            # compute_metrics calls get_nav which returns None, so compute inline
            import numpy as np
            nav_arr = np.array(curve.nav)
            returns = np.diff(nav_arr) / nav_arr[:-1]
            from datetime import datetime as _dt
            start = _dt.strptime(curve.dates[0][:10], "%Y-%m-%d")
            end = _dt.strptime(curve.dates[-1][:10], "%Y-%m-%d")
            years = (end - start).days / 365.25
            if years <= 0:
                raise HTTPException(status_code=404, detail=f"Metrics not available for {strategy_id}")
            total_return = nav_arr[-1] / nav_arr[0] - 1
            annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
            peak = np.maximum.accumulate(nav_arr)
            drawdown = (nav_arr - peak) / peak
            max_drawdown = float(np.min(drawdown))
            periods_per_year = len(returns) / years if years > 0 else 252
            mean_ret = np.mean(returns)
            std_ret = np.std(returns)
            sharpe = float(mean_ret / std_ret * np.sqrt(periods_per_year)) if std_ret > 0 else 0
            win_rate = float(np.sum(returns > 0) / len(returns))
            annual_vol = float(std_ret * np.sqrt(periods_per_year))
            from app.models.signal_schema import BacktestMetrics as BM
            result = BM(
                annual_return=round(annual_return, 4),
                max_drawdown=round(max_drawdown, 4),
                sharpe_ratio=round(sharpe, 2),
                win_rate=round(win_rate, 4),
                annual_volatility=round(annual_vol, 4),
                period_start=curve.dates[0],
                period_end=curve.dates[-1],
            )
        else:
            result = None
    else:
        result = nav_builder.compute_metrics(strategy_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Metrics not available for {strategy_id}")

    # Also compute and cache the nav curve
    if strategy_id == "macro-6cycle":
        pass  # curve already computed above
    else:
        curve = nav_builder.get_nav(strategy_id)
    if curve:
        await _save_nav_cache(strategy_id, curve, result)
    return result


@router.get("/history/{strategy_id}", response_model=List[SignalHistoryItem])
async def get_history(strategy_id: str, limit: int = 30):
    if strategy_id not in STRATEGY_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy_id}")

    # Try PG first
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
                    detail={
                        "holdings": holdings,
                        **detail,
                    },
                ))
            return items
    except Exception:
        pass

    # Fallback to parser (weekend-arb only)
    items = signal_parser.get_history(strategy_id, limit)
    return [SignalHistoryItem(**item) for item in items]


# ── Trigger endpoints ─────────────────────────────────────────

_RUNNERS = {
    "csi500-timing": run_csi500_timing,
    "macro-6cycle": run_macro_6cycle,
    "sharpe-rotation": run_sharpe_rotation,
    "us-fusion": run_us_fusion,
    "weekend-arb": run_weekend_arb,
}


@router.post("/trigger/{strategy_id}")
async def trigger_strategy(strategy_id: str, background_tasks: BackgroundTasks):
    """Manually trigger a single strategy run."""
    runner = _RUNNERS.get(strategy_id)
    if not runner:
        raise HTTPException(status_code=400, detail=f"No runner for strategy: {strategy_id}")
    background_tasks.add_task(runner)
    return {"status": "triggered", "strategy_id": strategy_id}


@router.post("/trigger-all")
async def trigger_all(background_tasks: BackgroundTasks):
    """Trigger all strategy runners."""
    for sid, runner in _RUNNERS.items():
        background_tasks.add_task(runner)
    return {"status": "triggered", "strategies": list(_RUNNERS.keys())}


@router.get("/scheduler-status")
async def scheduler_status():
    """Get scheduler status and last run times."""
    return get_scheduler_status()
