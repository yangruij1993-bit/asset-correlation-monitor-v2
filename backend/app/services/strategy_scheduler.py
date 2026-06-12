"""
Strategy signal scheduler.

Runs strategy scripts on schedule and writes output to directories
that the signal_parser reads from.

Schedule:
  08:00 daily  — 中证500择时 + 美股融合策略
  14:45 daily  — 中证500择时 (afternoon update)
  18:00 daily  — 宏观六周期 + 夏普轮动 + 周末套利
"""

import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger("strategy_scheduler")

# ── Strategy script configs ──────────────────────────────────

PROJECTS = {
    "quant_code": "/Users/xinghuazhang/ygr-project/行业轮动/quant_code_product/实盘代码-20260520/实盘代码",
    "us_fusion":  "/Users/xinghuazhang/ygr-project/行业轮动/美股融合策略实盘",
    "weekend_arb": "/Users/xinghuazhang/ygr-project/行业轮动/股指周末套利策略代码",
    # WUKONG: 移植时删除
    "wukong":     "/Users/xinghuazhang/ygr-project/wukong-git/quant_code_product/实盘代码-20260520/实盘代码",
}

# Python interpreters per project (use the project's own venv or fallback to system)
PYTHON = {
    "quant_code": "python3",
    "us_fusion":  "python3",
    "weekend_arb": "python3",
    "wukong":     "python3",
}

OUTPUT_DIRS = {
    "macro_6cycle": "/Users/xinghuazhang/ygr-project/行业轮动/quant_code_product/实盘代码-20260520/实盘代码/output/macro_cycle_rp/weight",
    "sharpe":       "/Users/xinghuazhang/ygr-project/行业轮动/quant_code_product/实盘代码-20260520/实盘代码/output/sharpe_ma252_divlv_gv_5050",
    "us_fusion":    "/Users/xinghuazhang/ygr-project/行业轮动/美股融合策略实盘/output/美股动量策略研究",
    "weekend_arb":  "/Users/xinghuazhang/ygr-project/行业轮动/股指周末套利策略代码",
}


_run_log: dict[str, str] = {}  # strategy_id -> "YYYY-MM-DD HH:MM" last success time


def _run(desc: str, cmd: list[str], cwd: str, timeout: int = 300) -> bool:
    """Run a subprocess command, log output."""
    log.info("[%s] Running: %s (cwd=%s)", desc, " ".join(cmd), cwd)
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        if result.stdout:
            for line in result.stdout.strip().split("\n")[-5:]:
                log.info("[%s] %s", desc, line)
        if result.returncode != 0:
            log.error("[%s] FAILED (rc=%d): %s", desc, result.returncode, result.stderr[-500:] if result.stderr else "")
            return False
        log.info("[%s] OK", desc)
        return True
    except subprocess.TimeoutExpired:
        log.error("[%s] TIMEOUT after %ds", desc, timeout)
        return False
    except Exception as e:
        log.error("[%s] ERROR: %s", desc, e)
        return False


# ── Strategy runners ──────────────────────────────────────────

def run_csi500_timing() -> bool:
    """Run CSI500 timing strategy via its main script."""
    cwd = PROJECTS["quant_code"]
    # The csi500_timing_core.py doesn't have __main__, so we run it via a wrapper
    script = """
import sys
sys.path.insert(0, '.')
from csi500_timing_core import run_timing, update_all_data, load_data
import pandas as pd
import tushare as ts
import os

pro = ts.pro_api(os.getenv('TUSHARE_TOKEN', ''))
data_dir = './data/csi500_timing_data'
os.makedirs(data_dir, exist_ok=True)
nav_df, d = run_timing(pro, data_dir, update=True, verbose=True)
today = pd.Timestamp.now().strftime('%Y%m%d')
out_dir = './output/csi500_timing'
os.makedirs(out_dir, exist_ok=True)
nav_df.to_csv(f'{out_dir}/csi500_timing_nav_{today}.csv', index=False, encoding='utf-8-sig')
# Also save latest signal
latest = nav_df.iloc[-1]
import json
signal = {
    'date': str(latest['trade_date'])[:10],
    'signal': float(latest['signal_csi500']),
    'nav': float(latest['nav_csi500']),
}
with open(f'{out_dir}/latest_signal.json', 'w') as f:
    json.dump(signal, f, ensure_ascii=False, indent=2)
print(f"Signal saved: {signal}")
"""
    # Write temp script and run it
    tmp = Path(cwd) / "_run_timing_tmp.py"
    tmp.write_text(script, encoding="utf-8")
    try:
        ok = _run("CSI500-Timing", [PYTHON["quant_code"], str(tmp)], cwd, timeout=600)
        if ok:
            _run_log["csi500-timing"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return ok
    finally:
        tmp.unlink(missing_ok=True)


def run_us_fusion() -> bool:
    """Run US fusion strategy daily signal pipeline."""
    cwd = PROJECTS["us_fusion"]
    ok = _run(
        "US-Fusion",
        [PYTHON["us_fusion"], "运行每日信号.py"],
        cwd, timeout=600,
    )
    if ok:
        _run_log["us-fusion"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return ok


def run_macro_6cycle() -> bool:
    """Run macro 6-cycle signal using the replacement script (no Excel COM)."""
    cwd = PROJECTS["wukong"]
    today = datetime.now().strftime("%Y%m%d")
    # Step 1: Update cycle from cached components
    ok = _run(
        "Macro-6Cycle (update)",
        [PYTHON["wukong"], "other_scripts/macro_cycle_from_sources.py",
         "--asof-date", today, "--promote"],
        cwd, timeout=120,
    )
    if not ok:
        log.warning("Macro-6Cycle: cycle update failed, using existing data")

    # Step 2: Run the allocation script to generate weight CSV
    alloc_script = "【ETF轮动实盘-宏观六周期轮动叠加500择时】a_share_index_allocation.py"
    ok2 = _run(
        "Macro-6Cycle (weights)",
        [PYTHON["wukong"], alloc_script, "history"],
        cwd, timeout=600,
    )
    if ok and ok2:
        _run_log["macro-6cycle"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return ok and ok2


def run_sharpe_rotation() -> bool:
    """Run sharpe rotation strategy — 'both' mode writes nav.csv + realtime CSV."""
    cwd = PROJECTS["quant_code"]
    script = "【ETF轮动实盘-有MA-简单夏普比筛选-多资产】strategy_sharpe_ma252_divlv_gv_5050.py"
    ok = _run(
        "Sharpe-Rotation",
        [PYTHON["quant_code"], script, "both"],
        cwd, timeout=600,
    )
    if ok:
        _run_log["sharpe-rotation"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return ok


def run_weekend_arb() -> bool:
    """Run weekend arbitrage strategy."""
    cwd = PROJECTS["weekend_arb"]
    script = "股指周末套利策略代码.py"
    ok = _run(
        "Weekend-Arb",
        [PYTHON["weekend_arb"], script],
        cwd, timeout=300,
    )
    if ok:
        _run_log["weekend-arb"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return ok


# ── Scheduled job groups ──────────────────────────────────────

def morning_csi500():
    """08:00 — CSI500 timing (first run of day)."""
    log.info("=== Morning CSI500 Timing ===")
    run_csi500_timing()


def afternoon_csi500():
    """14:45 — CSI500 timing (afternoon update) + Weekend arb."""
    log.info("=== Afternoon CSI500 + Weekend Arb ===")
    run_csi500_timing()
    run_weekend_arb()


def morning_us_fusion():
    """08:00 — US Fusion strategy."""
    log.info("=== Morning US Fusion ===")
    run_us_fusion()


def evening_strategies():
    """18:00 — Macro 6-cycle, Sharpe rotation."""
    log.info("=== Evening Strategies ===")
    run_macro_6cycle()
    run_sharpe_rotation()


# ── Scheduler lifecycle ───────────────────────────────────────

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    logging.basicConfig(level=logging.INFO)

    sched = BackgroundScheduler(timezone="Asia/Shanghai")

    # 08:00 — CSI500 timing + US fusion
    sched.add_job(morning_csi500, CronTrigger(hour=8, minute=0), id="morning_csi500")
    sched.add_job(morning_us_fusion, CronTrigger(hour=8, minute=3), id="morning_us_fusion")

    # 14:45 — CSI500 timing afternoon
    sched.add_job(afternoon_csi500, CronTrigger(hour=14, minute=45), id="afternoon_csi500")

    # 18:00 — Evening strategies
    sched.add_job(evening_strategies, CronTrigger(hour=18, minute=0), id="evening_strategies")

    sched.start()
    _scheduler = sched
    log.info("Strategy scheduler started (Asia/Shanghai timezone)")
    for job in sched.get_jobs():
        log.info("  %s: next run=%s", job.id, job.next_run_time)

    # Startup catch-up: if started after 8:10, run morning tasks immediately
    now = datetime.now()
    if now.hour > 8 or (now.hour == 8 and now.minute >= 10):
        if "csi500-timing" not in _run_log and "us-fusion" not in _run_log:
            log.info("Catch-up: running morning tasks (started after 08:10)")
            sched.add_job(morning_csi500, id="catchup_csi500")
            sched.add_job(morning_us_fusion, id="catchup_us_fusion")

    return sched


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("Strategy scheduler stopped")


def get_scheduler_status() -> dict:
    if not _scheduler:
        return {"running": False, "jobs": [], "last_runs": {}}
    jobs = []
    for j in _scheduler.get_jobs():
        jobs.append({
            "id": j.id,
            "next_run": str(j.next_run_time) if j.next_run_time else None,
        })
    return {"running": True, "jobs": jobs, "last_runs": dict(_run_log)}
