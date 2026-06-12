"""
Generic strategy signal parser.

Scans a directory for strategy signal JSON files and parses them into
SignalOverview / SignalDetail objects. No hardcoded strategy logic —
anyone can add a strategy by dropping a JSON file.

Directory structure:
  STRATEGY_DIR/
    my-strategy/
      signal_latest.json          (required)
      signal_history.jsonl        (optional, one JSON per line)
    another-strategy/
      signal_latest.json
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional

from app.models.signal_schema import (
    SignalOverview, SignalDetail, HoldingsItem,
    BacktestMetrics, SignalHistoryItem,
)

log = logging.getLogger(__name__)

STRATEGY_DIR = os.getenv("STRATEGY_DIR", "./strategies")


def _load_json(path: Path) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Failed to load %s: %s", path, e)
        return None


def _parse_overview(data: dict, strategy_id: str) -> SignalOverview:
    holdings = []
    for h in data.get("holdings", []):
        holdings.append(HoldingsItem(
            ticker=str(h.get("ticker", "")),
            name=str(h.get("name", "")),
            weight=float(h.get("weight", 0)),
        ))
    return SignalOverview(
        strategy_id=strategy_id,
        strategy_name=str(data.get("strategy_name", strategy_id)),
        signal_date=str(data.get("signal_date", "")),
        holdings=holdings,
        signal_detail=data.get("signal_detail", {}),
    )


def _parse_detail(data: dict, strategy_id: str) -> SignalDetail:
    overview = _parse_overview(data, strategy_id)
    detail = SignalDetail(
        strategy_id=overview.strategy_id,
        strategy_name=overview.strategy_name,
        signal_date=overview.signal_date,
        holdings=overview.holdings,
        signal_detail=overview.signal_detail,
    )
    # Optional NAV
    nav_data = data.get("nav")
    if nav_data and "values" in nav_data and len(nav_data["values"]) > 0:
        detail.nav_latest = float(nav_data["values"][-1])
    # Optional metrics
    m = data.get("metrics")
    if m:
        detail.metrics = BacktestMetrics(
            annual_return=float(m.get("annual_return", 0)),
            max_drawdown=float(m.get("max_drawdown", 0)),
            sharpe_ratio=float(m.get("sharpe_ratio", 0)),
            win_rate=float(m.get("win_rate", 0)),
            annual_volatility=float(m.get("annual_volatility", 0)) if "annual_volatility" in m else None,
            turnover=float(m.get("turnover", 0)) if "turnover" in m else None,
            period_start=str(m.get("period_start", "")),
            period_end=str(m.get("period_end", "")),
        )
    return detail


class GenericSignalParser:
    """Directory-scanning generic signal parser."""

    def discover_strategies(self) -> list[str]:
        """List all strategy IDs found in STRATEGY_DIR."""
        base = Path(STRATEGY_DIR)
        if not base.is_dir():
            return []
        ids = []
        for d in sorted(base.iterdir()):
            if d.is_dir() and (d / "signal_latest.json").exists():
                ids.append(d.name)
        return ids

    def get_overview(self, strategy_id: str) -> Optional[SignalOverview]:
        path = Path(STRATEGY_DIR) / strategy_id / "signal_latest.json"
        if not path.exists():
            return None
        data = _load_json(path)
        if not data:
            return None
        return _parse_overview(data, strategy_id)

    def get_overviews(self) -> list[SignalOverview]:
        results = []
        for sid in self.discover_strategies():
            try:
                ov = self.get_overview(sid)
                if ov:
                    results.append(ov)
            except Exception as e:
                log.warning("Error parsing strategy %s: %s", sid, e)
        return results

    def get_detail(self, strategy_id: str) -> Optional[SignalDetail]:
        path = Path(STRATEGY_DIR) / strategy_id / "signal_latest.json"
        if not path.exists():
            return None
        data = _load_json(path)
        if not data:
            return None
        return _parse_detail(data, strategy_id)

    def get_nav(self, strategy_id: str):
        """Return nav dates/values from signal JSON, or None."""
        from app.models.signal_schema import NavCurve
        path = Path(STRATEGY_DIR) / strategy_id / "signal_latest.json"
        if not path.exists():
            return None
        data = _load_json(path)
        nav_data = (data or {}).get("nav")
        if not nav_data or "dates" not in nav_data or "values" not in nav_data:
            return None
        return NavCurve(
            strategy_id=strategy_id,
            dates=nav_data["dates"],
            nav=nav_data["values"],
        )

    def get_history(self, strategy_id: str, limit: int = 30) -> list[SignalHistoryItem]:
        """Read signal_history.jsonl if present."""
        path = Path(STRATEGY_DIR) / strategy_id / "signal_history.jsonl"
        if not path.exists():
            return []
        items = []
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return []
        for line in reversed(lines[-limit:]):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                items.append(SignalHistoryItem(
                    date=str(entry.get("date", "")),
                    action=str(entry.get("action", "")),
                    detail=entry.get("detail", {}),
                ))
            except Exception:
                continue
        return items[:limit]


generic_signal_parser = GenericSignalParser()
