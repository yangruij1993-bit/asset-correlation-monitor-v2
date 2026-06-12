from pydantic import BaseModel
from typing import Literal, Optional

StrategyId = Literal[
    "macro-6cycle", "sharpe-rotation", "weekend-arb",
    "csi500-timing", "us-fusion", "cn-us-hk-timing",
    "spmo-usmv-64",
]


class HoldingsItem(BaseModel):
    ticker: str
    name: str
    weight: float


class BacktestMetrics(BaseModel):
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    annual_volatility: Optional[float] = None
    turnover: Optional[float] = None
    period_start: str
    period_end: str


class SignalOverview(BaseModel):
    strategy_id: StrategyId
    strategy_name: str
    signal_date: str
    holdings: list[HoldingsItem]
    signal_detail: dict


class SignalDetail(BaseModel):
    strategy_id: StrategyId
    strategy_name: str
    signal_date: str
    holdings: list[HoldingsItem]
    signal_detail: dict
    nav_latest: Optional[float] = None
    metrics: Optional[BacktestMetrics] = None


class NavCurve(BaseModel):
    strategy_id: StrategyId
    dates: list[str]
    nav: list[float]
    benchmark_nav: Optional[list[float]] = None
    benchmark_name: Optional[str] = None


class SignalHistoryItem(BaseModel):
    date: str
    action: str
    detail: dict
