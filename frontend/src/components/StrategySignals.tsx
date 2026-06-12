"use client";

import React, { useState, useEffect, useCallback } from "react";
import { SignalOverview, NavCurve, BacktestMetrics } from "@/lib/types";
import { fetchSignalOverviews, fetchNavCurve, fetchSignalMetrics } from "@/lib/api";
import { TrendingUp, Activity, BarChart3, LineChart, AlertTriangle, Inbox } from "lucide-react";
import clsx from "clsx";
import {
  LineChart as RechartsLineChart, Line, XAxis, YAxis, Tooltip,
  Legend, ResponsiveContainer, CartesianGrid,
} from "recharts";

const STRATEGY_IDS = [
  "macro-6cycle", "sharpe-rotation", "weekend-arb",
  "csi500-timing", "us-fusion", "cn-us-hk-timing",
  "spmo-usmv-64",
] as const;

type StrategySubTab = "overview" | (typeof STRATEGY_IDS)[number];

const STRATEGY_META: Record<string, { color: string; icon: React.ReactNode; desc: string }> = {
  "macro-6cycle": {
    color: "text-blue-400",
    icon: <Activity size={18} />,
    desc: "基于经济周期的风险平价轮动",
  },
  "sharpe-rotation": {
    color: "text-green-400",
    icon: <TrendingUp size={18} />,
    desc: "21日夏普比率的ETF轮动策略",
  },
  "weekend-arb": {
    color: "text-purple-400",
    icon: <TrendingUp size={18} />,
    desc: "5指数周末做多（沪深300/500/1000/2000/创业板）",
  },
  "csi500-timing": {
    color: "text-yellow-400",
    icon: <Activity size={18} />,
    desc: "MAB+基差+周末动量的择时策略",
  },
  "us-fusion": {
    color: "text-orange-400",
    icon: <TrendingUp size={18} />,
    desc: "SPMO/OFF5/USMV 融合策略",
  },
  "cn-us-hk-timing": {
    color: "text-cyan-400",
    icon: <Activity size={18} />,
    desc: "中港美股动量/均线择时",
  },
  "spmo-usmv-64": {
    color: "text-pink-400",
    icon: <TrendingUp size={18} />,
    desc: "SPMO/USMV 6:4 美股动量+低波择时",
  },
};

function CycleBadge({ cycleCode, cycleName }: { cycleCode: number; cycleName: string }) {
  const colors: Record<number, string> = {
    0: "bg-gray-500/20 text-gray-300 border-gray-500/30",
    1: "bg-green-500/20 text-green-400 border-green-500/30",
    2: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    3: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    4: "bg-orange-500/20 text-orange-400 border-orange-500/30",
    5: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    6: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
  };
  return (
    <span className={clsx("inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border", colors[cycleCode] || colors[0])}>
      周期{cycleCode}: {cycleName}
    </span>
  );
}

function StrategyCard({ data, onSelect }: { data: SignalOverview; onSelect: () => void }) {
  const meta = STRATEGY_META[data.strategy_id] || { color: "text-gray-400", icon: <Activity size={18} />, desc: "" };
  const detail = data.signal_detail;

  return (
    <div
      className="rounded-lg border border-border bg-surface p-4 hover:border-accent/50 transition-colors cursor-pointer"
      onClick={onSelect}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={meta.color}>{meta.icon}</span>
          <h4 className="font-semibold text-white">{data.strategy_name}</h4>
        </div>
        <span className="text-xs text-gray-500 font-mono">{data.signal_date}</span>
      </div>
      <p className="text-xs text-gray-500 mb-3">{meta.desc}</p>

      {/* Signal-specific badges */}
      <div className="flex flex-wrap gap-2 mb-3">
        {data.strategy_id === "weekend-arb" && detail.direction !== undefined && (
          <span className={clsx(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border",
            detail.direction === 1
              ? "bg-green-500/20 text-green-400 border-green-500/30"
              : "bg-gray-500/20 text-gray-400 border-gray-500/30"
          )}>
            {detail.direction === 1 ? "做多信号" : "空仓"}
          </span>
        )}
        {data.strategy_id === "macro-6cycle" && detail.cycle_code !== undefined && (
          <CycleBadge cycleCode={detail.cycle_code as number} cycleName={(detail.cycle_name as string) || ""} />
        )}
        {data.strategy_id === "sharpe-rotation" && detail.ma_above_252 !== undefined && (
          <span className={clsx(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border",
            detail.ma_above_252 ? "bg-green-500/20 text-green-400 border-green-500/30" : "bg-red-500/20 text-red-400 border-red-500/30"
          )}>
            万得全A {detail.ma_above_252 ? "站上" : "跌破"} MA252
          </span>
        )}
        {(data.strategy_id === "spmo-usmv-64" || data.strategy_id === "cn-us-hk-timing") && detail.timing_weight != null && (
          <span className={clsx(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border",
            (detail.timing_weight as number) > 0.5 ? "bg-green-500/20 text-green-400 border-green-500/30" :
            (detail.timing_weight as number) > 0 ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" :
            "bg-red-500/20 text-red-400 border-red-500/30"
          )}>
            仓位 {((detail.timing_weight as number) * 100).toFixed(0)}%
          </span>
        )}
        {data.strategy_id === "spmo-usmv-64" && detail.vol_regime != null && (
          <span className={clsx(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border",
            detail.vol_regime === "long" ? "bg-green-500/20 text-green-400 border-green-500/30" : "bg-orange-500/20 text-orange-400 border-orange-500/30"
          )}>
            {String(detail.vol_regime) === "long" ? "低波周期" : "高波周期"}
          </span>
        )}
      </div>

      {/* Holdings */}
      {data.holdings.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs text-gray-500 mb-1">持仓</div>
          {data.holdings.map((h, i) => {
            const isShort = h.weight < 0;
            const barWidth = Math.min(Math.abs(h.weight) * 100, 100);
            const barColor = isShort ? "bg-red-400" : "bg-accent";
            const label = isShort ? `做空 ${Math.abs(h.weight * 100).toFixed(1)}%` : `${(h.weight * 100).toFixed(1)}%`;
            return (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="text-gray-300">
                  {h.name} <span className="text-gray-600 text-xs font-mono">{h.ticker}</span>
                  {isShort && <span className="text-red-400 text-xs ml-1">做空</span>}
                </span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div className={clsx("h-full rounded-full", barColor)} style={{ width: `${barWidth}%` }} />
                  </div>
                  <span className={clsx("font-mono text-xs w-16 text-right", isShort ? "text-red-400" : "text-gray-400")}>
                    {label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── NAV Chart Component ──────────────────────────────────────

function NavChartSection({ strategyId }: { strategyId: string }) {
  const [navData, setNavData] = useState<NavCurve | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchNavCurve(strategyId)
      .then(data => { if (!cancelled) setNavData(data); })
      .catch(e => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [strategyId, retryKey]);

  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-surface p-4">
        <div className="flex items-center gap-2 mb-4">
          <LineChart size={16} className="text-accent" />
          <h4 className="font-semibold text-white">净值曲线</h4>
        </div>
        <div className="space-y-3">
          <div className="h-4 bg-gray-700/50 rounded animate-pulse w-1/3" />
          <div className="h-[300px] bg-gray-700/30 rounded animate-pulse" />
        </div>
      </div>
    );
  }

  if (error || !navData || navData.dates.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-surface p-6 text-center">
        {error ? (
          <AlertTriangle size={24} className="mx-auto mb-2 text-yellow-500" />
        ) : (
          <Inbox size={24} className="mx-auto mb-2 text-gray-500" />
        )}
        <p className="text-gray-500 text-sm">{error || "暂无净值数据"}</p>
        {error && (
          <button
            onClick={() => setRetryKey(k => k + 1)}
            className="mt-2 text-xs text-accent hover:underline"
          >
            重试
          </button>
        )}
      </div>
    );
  }

  const chartData = navData.dates.map((d, i) => ({
    date: d.length > 10 ? d.slice(0, 10) : d,
    nav: navData.nav[i],
    ...(navData.benchmark_nav ? { benchmark: navData.benchmark_nav[i] } : {}),
  }));

  // Calculate interval to show ~1 tick per year (assume ~252 trading days/year)
  const tickInterval = chartData.length > 252
    ? Math.floor(chartData.length / (Number(chartData[chartData.length - 1].date.slice(0, 4)) - Number(chartData[0].date.slice(0, 4)) + 1))
    : 0;

  // Check if all nav values are the same (flat placeholder)
  const isFlat = navData.nav.every(v => v === navData.nav[0]);

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center gap-2 mb-4">
        <LineChart size={16} className="text-accent" />
        <h4 className="font-semibold text-white">净值曲线</h4>
        {isFlat && (
          <span className="text-xs text-yellow-500 bg-yellow-500/10 px-2 py-0.5 rounded">
            权重数据（需要价格数据计算实际净值）
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={350}>
        <RechartsLineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis
            dataKey="date"
            interval={tickInterval || "preserveStartEnd"}
            tick={{ fill: "#999", fontSize: 11 }}
            tickFormatter={(v: string) => v.slice(0, 4)}
            minTickGap={40}
          />
          <YAxis tick={{ fill: "#999", fontSize: 11 }} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ backgroundColor: "#1a1a2e", border: "1px solid #333", borderRadius: 6 }}
            labelStyle={{ color: "#999" }}
          />
          <Legend />
          <Line type="monotone" dataKey="nav" stroke="#6366f1" dot={false} strokeWidth={2} name="策略净值" />
          {navData.benchmark_nav && (
            <Line type="monotone" dataKey="benchmark" stroke="#666" dot={false} strokeWidth={1} strokeDasharray="5 5" name={navData.benchmark_name || "基准"} />
          )}
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Metrics Table Component ──────────────────────────────────

function MetricsSection({ strategyId }: { strategyId: string }) {
  const [metrics, setMetrics] = useState<BacktestMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchSignalMetrics(strategyId)
      .then(data => { if (!cancelled) setMetrics(data); })
      .catch(() => { if (!cancelled) setError("no-data"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [strategyId, retryKey]);

  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-surface p-4">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 size={16} className="text-accent" />
          <h4 className="font-semibold text-white">回测指标</h4>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-background rounded-lg p-3 animate-pulse">
              <div className="h-3 bg-gray-700/50 rounded w-16 mb-2" />
              <div className="h-6 bg-gray-700/50 rounded w-12" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="rounded-lg border border-border bg-surface p-6 text-center">
        <Inbox size={24} className="mx-auto mb-2 text-gray-500" />
        <p className="text-gray-500 text-sm">暂无回测数据</p>
      </div>
    );
  }

  const rows = [
    { label: "年化收益率", value: `${(metrics.annual_return * 100).toFixed(2)}%`, color: metrics.annual_return >= 0 ? "text-green-400" : "text-red-400" },
    { label: "最大回撤", value: `${(metrics.max_drawdown * 100).toFixed(2)}%`, color: "text-red-400" },
    { label: "夏普比率", value: metrics.sharpe_ratio.toFixed(2), color: metrics.sharpe_ratio >= 1 ? "text-green-400" : "text-yellow-400" },
    { label: "胜率", value: `${(metrics.win_rate * 100).toFixed(1)}%`, color: metrics.win_rate >= 0.5 ? "text-green-400" : "text-yellow-400" },
    ...(metrics.annual_volatility !== null ? [{ label: "年化波动率", value: `${(metrics.annual_volatility * 100).toFixed(2)}%`, color: "text-gray-300" }] : []),
    ...(metrics.turnover !== null ? [{ label: "换手率", value: `${(metrics.turnover * 100).toFixed(2)}%`, color: "text-gray-300" }] : []),
  ];

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 size={16} className="text-accent" />
        <h4 className="font-semibold text-white">回测指标</h4>
        <span className="text-xs text-gray-500 ml-auto">
          {metrics.period_start} ~ {metrics.period_end}
        </span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {rows.map((r, i) => (
          <div key={i} className="bg-background rounded-lg p-3">
            <div className="text-xs text-gray-500 mb-1">{r.label}</div>
            <div className={clsx("text-lg font-semibold font-mono", r.color)}>{r.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Momentum Timing Detail (for spmo-usmv-64) ────────────────

function MomentumTimingDetail({ detail }: { detail: Record<string, unknown> }) {
  const regime = detail.vol_regime as string;
  const isLowVol = regime === "long";
  const weight = detail.timing_weight as number;
  const mmtLong = detail.momentum_long as Record<string, number> || {};
  const mmtShort = detail.momentum_short as Record<string, number> || {};

  return (
    <div className="rounded-lg border border-border bg-surface p-4 space-y-3">
      <div className="flex items-center gap-2">
        <AlertTriangle size={14} className="text-yellow-400" />
        <h4 className="font-semibold text-white">择时信号详情</h4>
        <span className="text-xs text-gray-500 ml-auto font-mono">
          标的: {String(detail.bench ?? "")} | 收盘: {typeof detail.close === "number" ? detail.close.toFixed(2) : String(detail.close ?? "")}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-background rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">仓位权重</div>
          <div className={clsx("text-lg font-semibold font-mono", weight > 0.5 ? "text-green-400" : weight > 0 ? "text-yellow-400" : "text-red-400")}>
            {(weight * 100).toFixed(0)}%
          </div>
        </div>
        <div className="bg-background rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">波动率</div>
          <div className="text-lg font-semibold font-mono text-gray-300">
            {typeof detail.volatility === "number" ? (detail.volatility * 100).toFixed(1) + "%" : "-"}
          </div>
        </div>
        <div className="bg-background rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">波动率状态</div>
          <div className={clsx("text-sm font-semibold", isLowVol ? "text-green-400" : "text-orange-400")}>
            {isLowVol ? "低波（长周期）" : "高波（短周期）"}
          </div>
        </div>
        <div className="bg-background rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">日涨跌幅</div>
          <div className={clsx("text-lg font-semibold font-mono", typeof detail.daily_chg === "number" && detail.daily_chg >= 0 ? "text-green-400" : "text-red-400")}>
            {typeof detail.daily_chg === "number" ? (detail.daily_chg * 100).toFixed(2) + "%" : "-"}
          </div>
        </div>
      </div>

      {/* Momentum table */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <div className="text-xs text-gray-500 mb-2">{isLowVol ? "► 长周期动量（当前使用）" : "长周期动量"}</div>
          <div className="space-y-1">
            {Object.entries(mmtLong).sort(([a], [b]) => Number(a) - Number(b)).map(([period, val]) => (
              <div key={period} className="flex items-center justify-between text-sm">
                <span className="text-gray-400">{period}日动量</span>
                <span className={clsx("font-mono", val >= 0 ? "text-green-400" : "text-red-400")}>
                  {(val * 100).toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-2">{!isLowVol ? "► 短周期动量（当前使用）" : "短周期动量"}</div>
          <div className="space-y-1">
            {Object.entries(mmtShort).sort(([a], [b]) => Number(a) - Number(b)).map(([period, val]) => (
              <div key={period} className="flex items-center justify-between text-sm">
                <span className="text-gray-400">{period}日动量</span>
                <span className={clsx("font-mono", val >= 0 ? "text-green-400" : "text-red-400")}>
                  {(val * 100).toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── CN/US/HK Multi-Region Timing Detail ──────────────────────

const REGION_LABELS: Record<string, string> = {
  us: "美股 (SPX)",
  hk: "恒生科技",
  cn300: "沪深300",
  cn1000: "中证1000",
};

function CnUsHkTimingDetail({ detail }: { detail: Record<string, unknown> }) {
  const situation = detail.current_situation as Record<string, Record<string, unknown>> || {};
  const allocs = [
    { key: "us", label: "美股", alloc: detail.us_alloc as number },
    { key: "hk", label: "港股", alloc: detail.hk_alloc as number },
    { key: "cn300", label: "沪深300", alloc: detail.cn300_alloc as number },
    { key: "cn1000", label: "中证1000", alloc: detail.cn1000_alloc as number },
  ].filter(a => a.alloc > 0);

  return (
    <div className="rounded-lg border border-border bg-surface p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Activity size={14} className="text-cyan-400" />
        <h4 className="font-semibold text-white">各区域择时详情</h4>
        <span className="text-xs text-gray-500 ml-auto">
          配比: {allocs.map(a => `${a.label} ${((a.alloc as number) * 100).toFixed(0)}%`).join(" / ")}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Object.entries(situation).map(([region, data]) => {
          if (data.error) {
            return (
              <div key={region} className="bg-background rounded-lg p-3">
                <div className="text-xs text-gray-500 mb-1">{REGION_LABELS[region] || region}</div>
                <div className="text-sm text-red-400">{String(data.error)}</div>
              </div>
            );
          }
          const w = data.timing_weight as number;
          const regime = data.vol_regime as string;
          const mmtLong = data.momentum_long as Record<string, number> || {};
          const mmtShort = data.momentum_short as Record<string, number> || {};
          const activeMmt = regime === "long" ? mmtLong : mmtShort;

          return (
            <div key={region} className="bg-background rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-white">{REGION_LABELS[region] || region}</span>
                <span className={clsx("text-xs font-mono px-2 py-0.5 rounded border",
                  w > 0.5 ? "bg-green-500/20 text-green-400 border-green-500/30" :
                  w > 0 ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" :
                  "bg-red-500/20 text-red-400 border-red-500/30"
                )}>
                  仓位 {(w * 100).toFixed(0)}%
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <span className="text-gray-500">收盘</span>
                  <div className="font-mono text-gray-300">{typeof data.close === "number" ? data.close.toFixed(2) : "-"}</div>
                </div>
                <div>
                  <span className="text-gray-500">波动率</span>
                  <div className="font-mono text-gray-300">{typeof data.volatility === "number" ? (data.volatility * 100).toFixed(1) + "%" : "-"}</div>
                </div>
                <div>
                  <span className="text-gray-500">状态</span>
                  <div className={clsx("font-mono", regime === "long" ? "text-green-400" : "text-orange-400")}>
                    {regime === "long" ? "低波" : "高波"}
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-1">
                {Object.entries(activeMmt).map(([period, val]) => (
                  <span key={period} className={clsx(
                    "text-[10px] font-mono px-1.5 py-0.5 rounded",
                    val >= 0 ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"
                  )}>
                    {period}d {(val as number * 100).toFixed(1)}%
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Strategy Detail View ─────────────────────────────────────

function StrategyDetailView({ strategyId, overview }: { strategyId: string; overview: SignalOverview }) {
  const meta = STRATEGY_META[strategyId] || { color: "text-gray-400", icon: <Activity size={18} />, desc: "" };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const detail = overview.signal_detail as Record<string, any>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <span className={meta.color}>{meta.icon}</span>
        <div>
          <h3 className="text-xl font-semibold text-white">{overview.strategy_name}</h3>
          <p className="text-sm text-gray-500">{meta.desc} | 信号日期: {overview.signal_date}</p>
        </div>
      </div>

      {/* Signal-specific badges */}
      {(strategyId === "macro-6cycle" || strategyId === "sharpe-rotation" || strategyId === "weekend-arb") ? (
        <div className="flex flex-wrap gap-2">
          {strategyId === "weekend-arb" && detail.direction !== undefined ? (
            <span className={clsx(
              "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border",
              detail.direction === 1
                ? "bg-green-500/20 text-green-400 border-green-500/30"
                : "bg-gray-500/20 text-gray-400 border-gray-500/30"
            )}>
              {detail.direction === 1 ? "做多信号" : "空仓"}
            </span>
          ) : null}
          {strategyId === "macro-6cycle" && detail.cycle_code !== undefined ? (
            <CycleBadge cycleCode={detail.cycle_code} cycleName={detail.cycle_name || ""} />
          ) : null}
          {strategyId === "sharpe-rotation" && detail.ma_above_252 !== undefined ? (
            <span className={clsx(
              "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border",
              detail.ma_above_252 ? "bg-green-500/20 text-green-400 border-green-500/30" : "bg-red-500/20 text-red-400 border-red-500/30"
            )}>
              万得全A {detail.ma_above_252 ? "站上" : "跌破"} MA252
            </span>
          ) : null}
        </div>
      ) : null}

      {/* Momentum Timing Detail for spmo-usmv-64 */}
      {strategyId === "spmo-usmv-64" && detail && (
        <MomentumTimingDetail detail={detail} />
      )}

      {/* Multi-region timing detail for cn-us-hk-timing */}
      {strategyId === "cn-us-hk-timing" && detail.current_situation && (
        <CnUsHkTimingDetail detail={detail} />
      )}

      {/* Holdings */}
      <div className="rounded-lg border border-border bg-surface p-4">
        <h4 className="font-semibold text-white mb-3">当前持仓</h4>
        <div className="space-y-2">
          {overview.holdings.map((h, i) => {
            const barWidth = Math.min(Math.abs(h.weight) * 100, 100);
            const isShort = h.weight < 0;
            return (
              <div key={i} className="flex items-center justify-between">
                <span className="text-gray-300 text-sm">
                  {h.name} <span className="text-gray-600 text-xs font-mono">{h.ticker}</span>
                </span>
                <div className="flex items-center gap-3">
                  <div className="w-32 h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div className={clsx("h-full rounded-full", isShort ? "bg-red-400" : "bg-accent")} style={{ width: `${barWidth}%` }} />
                  </div>
                  <span className={clsx("font-mono text-sm w-20 text-right", isShort ? "text-red-400" : "text-gray-300")}>
                    {isShort ? `${(h.weight * 100).toFixed(1)}%` : `${(h.weight * 100).toFixed(1)}%`}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* NAV Chart */}
      <NavChartSection strategyId={strategyId} />

      {/* Metrics */}
      <MetricsSection strategyId={strategyId} />
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────

export default function StrategySignals() {
  const [signals, setSignals] = useState<SignalOverview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [subTab, setSubTab] = useState<StrategySubTab>("overview");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSignalOverviews();
      setSignals(data);
    } catch (e) {
      setError("Failed to load strategy signals");
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex flex-wrap gap-1 border-b border-border/50">
          <div className="px-4 py-2 text-sm text-gray-500">Loading...</div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="rounded-lg border border-border bg-surface p-4 animate-pulse">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-4 h-4 bg-gray-700/50 rounded" />
                <div className="h-5 bg-gray-700/50 rounded w-28" />
                <div className="h-4 bg-gray-700/50 rounded w-16 ml-auto" />
              </div>
              <div className="h-3 bg-gray-700/50 rounded w-3/4 mb-3" />
              <div className="space-y-2">
                {[...Array(3)].map((_, j) => (
                  <div key={j} className="flex items-center justify-between">
                    <div className="h-3 bg-gray-700/50 rounded w-20" />
                    <div className="h-3 bg-gray-700/50 rounded w-24" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card text-center py-12">
        <AlertTriangle size={32} className="mx-auto mb-3 text-red-400" />
        <p className="text-red-400 mb-2">{error}</p>
        <p className="text-gray-500 text-sm mb-4">请检查后端服务是否正常运行</p>
        <button onClick={loadData} className="btn btn-secondary">重试</button>
      </div>
    );
  }

  const selectedSignal = signals.find(s => s.strategy_id === subTab);

  return (
    <div className="space-y-6">
      {/* Sub-tab navigation */}
      <div className="flex flex-wrap gap-1 border-b border-border/50">
        <button
          onClick={() => setSubTab("overview")}
          className={clsx(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            subTab === "overview"
              ? "border-accent text-accent"
              : "border-transparent text-gray-400 hover:text-gray-300"
          )}
        >
          Overview
        </button>
        {STRATEGY_IDS.map(sid => {
          const meta = STRATEGY_META[sid];
          const signal = signals.find(s => s.strategy_id === sid);
          return (
            <button
              key={sid}
              onClick={() => setSubTab(sid)}
              className={clsx(
                "flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                subTab === sid
                  ? "border-accent text-accent"
                  : "border-transparent text-gray-400 hover:text-gray-300"
              )}
            >
              {meta?.icon}
              {signal?.strategy_name || sid}
            </button>
          );
        })}
      </div>

      {/* Content */}
      {subTab === "overview" ? (
        <>
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-semibold text-accent">Strategy Signals</h3>
            <span className="text-sm text-gray-500">{signals.length} strategies</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {signals.map((s) => (
              <StrategyCard key={s.strategy_id} data={s} onSelect={() => setSubTab(s.strategy_id as StrategySubTab)} />
            ))}
          </div>
        </>
      ) : selectedSignal ? (
        <StrategyDetailView strategyId={subTab} overview={selectedSignal} />
      ) : (
        <div className="card text-center py-12">
          <Inbox size={32} className="mx-auto mb-3 text-gray-500" />
          <p className="text-gray-400">该策略暂无数据</p>
          <button
            onClick={() => setSubTab("overview")}
            className="text-sm text-accent hover:underline mt-2"
          >
            返回概览
          </button>
        </div>
      )}
    </div>
  );
}
