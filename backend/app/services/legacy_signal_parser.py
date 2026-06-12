"""
Unified signal parser for all 5 strategies.
Reads actual strategy output CSV/JSON files and normalizes to SignalOverview/SignalDetail.
"""

import os
import glob
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

from app.config.assets import TICKER_NAMES
from app.models.signal_schema import SignalOverview, SignalDetail, HoldingsItem, BacktestMetrics

# Strategy data paths — configured via env or defaults
_BASE = os.getenv(
    "STRATEGY_DATA_DIR",
    "/Users/xinghuazhang/ygr-project/行业轮动/quant_code_product/实盘代码-20260520/实盘代码",
)

STRATEGY_PATHS: dict[str, str] = {
    "macro-6cycle": os.path.join(_BASE, "output/macro_cycle_rp/weight"),
    "sharpe-rotation": os.path.join(_BASE, "output/sharpe_ma252_divlv_gv_5050"),
    "weekend-arb": os.getenv(
        "WEEKEND_ARB_DIR",
        "/Users/xinghuazhang/ygr-project/行业轮动/股指周末套利策略代码",
    ),
    "csi500-timing": os.getenv(
        "CSI500_TIMING_DIR",
        "/Users/xinghuazhang/ygr-project/资产配置监控/实盘_unzip/实盘/ETF实盘代码/data",
    ),
    "us-fusion": os.getenv(
        "US_FUSION_DIR",
        "/Users/xinghuazhang/ygr-project/资产配置监控/实盘/美股实盘/美股融合策略实盘/output/美股动量策略研究",
    ),
    "cn-us-hk-timing": os.getenv(
        "CN_US_HK_TIMING_DIR",
        "/Users/xinghuazhang/ygr-project/资产配置监控/实盘/中美港股仓位择时-每日汇报",
    ),
}

STRATEGY_NAMES: dict[str, str] = {
    "macro-6cycle": "宏观六周期风险平价",
    "sharpe-rotation": "夏普动量轮动",
    "weekend-arb": "周末套利",
    "csi500-timing": "中证500择时",
    "us-fusion": "美股融合策略",
    "cn-us-hk-timing": "中美港择时",
    "spmo-usmv-64": "SPMO/USMV 6:4动量择时",
}

# Name mapping for strategy-internal codes
_SEC_NAME_MAP = {
    "metal": "有色金属",
    "cyb": "创业板",
    "bond30": "国债30",
    "gold": "黄金",
    "dividend": "红利低波",
    "成长100": "成长100",
    "价值100": "价值100",
    "创业板50": "创业板50",
    "红利低波": "红利低波",
    "SPMO.P": "美股动量",
    "USMV.BAT": "美股低波",
    "SETF.HSTECH.HI": "恒生科技",
    "SETF.000300.SH": "沪深300",
    "SETF.000852.SH": "中证1000",
}


def _ticker_display(ticker: str) -> str:
    return TICKER_NAMES.get(ticker, ticker)


class SignalParser:
    def get_overview(self, strategy_id: str) -> SignalOverview | None:
        handler = {
            "macro-6cycle": self._parse_macro_6cycle,
            "sharpe-rotation": self._parse_sharpe_rotation,
            "weekend-arb": self._parse_weekend_arb,
            "csi500-timing": self._parse_csi500_timing,
            "us-fusion": self._parse_us_fusion,
            "cn-us-hk-timing": self._parse_cn_us_hk_timing,
            "spmo-usmv-64": self._parse_spmo_usmv_64,
        }.get(strategy_id)
        if not handler:
            return None
        return handler()

    def get_overviews(self) -> list[SignalOverview]:
        results = []
        for sid in ["macro-6cycle", "sharpe-rotation", "weekend-arb", "csi500-timing", "us-fusion", "cn-us-hk-timing", "spmo-usmv-64"]:
            try:
                ov = self.get_overview(sid)
                if ov:
                    results.append(ov)
            except Exception:
                pass
        return results

    def get_detail(self, strategy_id: str) -> SignalDetail | None:
        ov = self.get_overview(strategy_id)
        if not ov:
            return None
        return SignalDetail(
            strategy_id=ov.strategy_id,
            strategy_name=ov.strategy_name,
            signal_date=ov.signal_date,
            holdings=ov.holdings,
            signal_detail=ov.signal_detail,
        )

    # ── macro-6cycle ──────────────────────────────────────────

    def _parse_macro_6cycle(self) -> SignalOverview | None:
        path = STRATEGY_PATHS["macro-6cycle"]
        pattern = os.path.join(path, "weights_macro_cycle_rp_etf_*.csv")
        files = glob.glob(pattern)
        # WUKONG: 移植时删除
        wukong_path = "/Users/xinghuazhang/ygr-project/wukong-git/quant_code_product/实盘代码-20260520/实盘代码/output/macro_cycle_rp/weight"
        wukong_pattern = os.path.join(wukong_path, "weights_macro_cycle_rp_etf_*.csv")
        files.extend(glob.glob(wukong_pattern))
        # Sort by filename (contains date), take latest
        files = sorted(files, key=lambda f: os.path.basename(f))
        if not files:
            return None
        latest = files[-1]
        df = pd.read_csv(latest, encoding="utf-8-sig")
        if df.empty:
            return None
        date_str = str(df["date"].iloc[-1])[:8]
        signal_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        latest_rows = df[df["date"] == df["date"].iloc[-1]]
        cycle_code = int(latest_rows["cycle_code"].iloc[0]) if not latest_rows.empty else 0
        # Override cycle_code from economic_cycle.csv (more up-to-date)
        cycle_code = self._read_latest_cycle_code() or cycle_code
        holdings = []
        for _, row in latest_rows.iterrows():
            ticker = str(row["windcode"])
            name = _SEC_NAME_MAP.get(str(row.get("sec_name", "")), _ticker_display(ticker))
            holdings.append(HoldingsItem(ticker=ticker, name=name, weight=round(float(row["weight"]), 4)))
        return SignalOverview(
            strategy_id="macro-6cycle",
            strategy_name=STRATEGY_NAMES["macro-6cycle"],
            signal_date=signal_date,
            holdings=holdings,
            signal_detail={"cycle_code": cycle_code, "cycle_name": self._cycle_name(cycle_code)},
        )

    def _read_latest_cycle_code(self) -> int | None:
        """Read the latest cycle code from economic_cycle.csv (updated by scheduler)."""
        for candidate in [
            os.path.join(_BASE, "data", "economic_cycle.csv"),
            os.path.join(_BASE, "..", "data", "economic_cycle.csv"),
            # WUKONG: 移植时删除
            "/Users/xinghuazhang/ygr-project/wukong-git/quant_code_product/实盘代码-20260520/实盘代码/data/economic_cycle.csv",
        ]:
            p = os.path.normpath(candidate)
            if os.path.exists(p):
                try:
                    ec = pd.read_csv(p, header=None, names=["date", "cycle_code"])
                    if not ec.empty:
                        return int(ec.iloc[-1]["cycle_code"])
                except Exception:
                    pass
        return None

    @staticmethod
    def _cycle_name(code: int) -> str:
        names = {0: "衰退", 1: "复苏", 2: "扩张早", 3: "扩张晚", 4: "滞胀", 5: "收缩", 6: "货币扩张"}
        return names.get(code, f"周期{code}")

    # ── sharpe-rotation ───────────────────────────────────────

    def _parse_sharpe_rotation(self) -> SignalOverview | None:
        path = STRATEGY_PATHS["sharpe-rotation"]
        detail_file = os.path.join(path, "realtime_signal_detail.csv")
        summary_file = os.path.join(path, "realtime_signal_summary.csv")
        if not os.path.exists(detail_file):
            return None
        df = pd.read_csv(detail_file, encoding="utf-8-sig")
        if df.empty:
            return None
        signal_date = str(df["当前日期"].iloc[0])

        # Read summary to get final choices per group
        final_choices: dict[str, str] = {}
        ma_above = None
        if os.path.exists(summary_file):
            sdf = pd.read_csv(summary_file, encoding="utf-8-sig")
            if not sdf.empty:
                ma_above = bool(sdf.iloc[0].get("万得全A是否站上MA252", False))
                for _, row in sdf.iterrows():
                    group = str(row.get("分组", ""))
                    choice = str(row.get("最终选择", ""))
                    if group and choice:
                        final_choices[group] = choice

        holdings = []
        n_groups = len(final_choices) or 1
        group_weight = round(1.0 / n_groups, 4)
        for _, row in df.iterrows():
            etf = str(row.get("ETF", ""))
            asset_name = str(row.get("资产", ""))
            group = str(row.get("分组", ""))
            is_selected = final_choices.get(group) == asset_name
            weight = group_weight if is_selected else 0.0
            sec_name = _SEC_NAME_MAP.get(asset_name, asset_name)
            holdings.append(HoldingsItem(ticker=etf, name=sec_name, weight=weight))

        return SignalOverview(
            strategy_id="sharpe-rotation",
            strategy_name=STRATEGY_NAMES["sharpe-rotation"],
            signal_date=signal_date,
            holdings=holdings,
            signal_detail={
                "ma_above_252": ma_above,
                "groups": df["分组"].unique().tolist() if "分组" in df.columns else [],
            },
        )

    # ── weekend-arb ───────────────────────────────────────────

    WEEKEND_ARB_INDICES = {
        "000300.SH": "沪深300",
        "000905.SH": "中证500",
        "000852.SH": "中证1000",
        "932000.CSI": "中证2000",
        "399006.SZ": "创业板指",
    }
    WEEKEND_ARB_MA_WINDOW = 20
    WEEKEND_ARB_THRESHOLD = 0.01  # daily return > 1% triggers long

    def _parse_weekend_arb(self) -> SignalOverview | None:
        # Try Oracle-based live calculation first
        result = self._parse_weekend_arb_oracle()
        if result:
            return result
        # Fallback to CSV
        return self._parse_weekend_arb_csv()

    def _parse_weekend_arb_oracle(self) -> SignalOverview | None:
        """Calculate weekend arb signals from Oracle AIndexEODPrices."""
        from app.services.data_service_oracle import oracle_data_service
        import oracledb, numpy as np

        if not all([oracle_data_service.user, oracle_data_service.password, oracle_data_service.dsn]):
            return None

        try:
            oracledb.init_oracle_client(lib_dir=os.getenv("ORACLE_CLIENT_DIR", ""))
        except Exception:
            pass

        try:
            conn = oracledb.connect(
                user=oracle_data_service.user,
                password=oracle_data_service.password,
                dsn=oracle_data_service.dsn,
            )
        except Exception:
            return None

        try:
            schema = os.getenv("ORACLE_SCHEMA", "WKWD_SYNC")
            codes = list(self.WEEKEND_ARB_INDICES.keys())
            ticker_list = ", ".join(f"'{t}'" for t in codes)
            # Get enough history for MA20 + recent weeks
            sql = f"""
                SELECT S_INFO_WINDCODE AS ticker, TRADE_DT AS trade_date, S_DQ_CLOSE AS close
                FROM {schema}.AIndexEODPrices
                WHERE S_INFO_WINDCODE IN ({ticker_list})
                AND TRADE_DT >= '20260101'
                ORDER BY TRADE_DT, S_INFO_WINDCODE
            """
            df = pd.read_sql(sql, conn)
            if df.empty:
                return None

            df["TRADE_DATE"] = pd.to_datetime(df["TRADE_DATE"], format="%Y%m%d")
            pivot = df.pivot(index="TRADE_DATE", columns="TICKER", values="CLOSE")
            pivot = pivot.sort_index().astype(float)

            # Get trading calendar
            all_dates = sorted(pivot.index.tolist())

            # Find week-last trading days (next trading day is 2+ calendar days away)
            week_last_indices = []
            for i in range(len(all_dates) - 1):
                gap = (all_dates[i + 1] - all_dates[i]).days
                if gap > 1:
                    week_last_indices.append(i)

            if not week_last_indices:
                return None

            # Latest week-last date
            signal_date_idx = week_last_indices[-1]
            signal_date = all_dates[signal_date_idx]
            signal_date_str = signal_date.strftime("%Y-%m-%d")

            holdings = []
            triggered_count = 0
            for code, name in self.WEEKEND_ARB_INDICES.items():
                if code not in pivot.columns:
                    holdings.append(HoldingsItem(ticker=code, name=name, weight=0.0))
                    continue
                series = pivot[code].dropna()
                if signal_date not in series.index:
                    holdings.append(HoldingsItem(ticker=code, name=name, weight=0.0))
                    continue

                close_val = series.loc[signal_date]

                # MA20
                loc = series.index.get_loc(signal_date)
                if loc < self.WEEKEND_ARB_MA_WINDOW:
                    holdings.append(HoldingsItem(ticker=code, name=name, weight=0.0))
                    continue
                ma20 = series.iloc[loc - self.WEEKEND_ARB_MA_WINDOW + 1:loc + 1].mean()

                # Daily return
                if loc > 0:
                    prev_close = series.iloc[loc - 1]
                    daily_ret = (close_val - prev_close) / prev_close
                else:
                    daily_ret = 0.0

                # Signal: long if close > MA20 AND daily_return > threshold
                triggered = (close_val > ma20) and (daily_ret > self.WEEKEND_ARB_THRESHOLD)
                if triggered:
                    triggered_count += 1
                holdings.append(HoldingsItem(
                    ticker=code, name=name,
                    weight=round(1.0 / len(self.WEEKEND_ARB_INDICES), 4) if triggered else 0.0,
                ))

            return SignalOverview(
                strategy_id="weekend-arb",
                strategy_name=STRATEGY_NAMES["weekend-arb"],
                signal_date=signal_date_str,
                holdings=holdings,
                signal_detail={
                    "triggered_count": triggered_count,
                    "total_indices": len(self.WEEKEND_ARB_INDICES),
                    "is_week_last": True,
                },
            )
        except Exception:
            return None
        finally:
            conn.close()

    def _parse_weekend_arb_csv(self) -> SignalOverview | None:
        """Fallback: read signals from legacy CSV."""
        path = STRATEGY_PATHS["weekend-arb"]
        csv_file = os.path.join(path, "all_signals_ic_weekend_speculation.csv")
        if not os.path.exists(csv_file):
            return None
        df = pd.read_csv(csv_file, encoding="utf-8-sig")
        if df.empty:
            return None

        df["signal_date"] = pd.to_datetime(df["signal_date"])
        if "is_week_last" in df.columns:
            df["is_week_last"] = df["is_week_last"].astype(str).str.lower().isin({"true", "1"})
            df = df[df["is_week_last"]]
        if "trade_status" in df.columns:
            df = df[df["trade_status"].astype(str).str.strip() != "pending_exit"]
        if df.empty:
            return None

        latest_per_index = df.groupby("ts_code").last().reset_index()
        signal_date = str(df.iloc[-1]["signal_date"].date())

        weight = 0.2
        holdings = []
        for _, row in latest_per_index.iterrows():
            direction = int(row.get("direction", 0))
            code = str(row.get("ts_code", ""))
            name = self.WEEKEND_ARB_INDICES.get(code, code)
            w = weight if direction == 1 else 0.0
            holdings.append(HoldingsItem(ticker=code, name=name, weight=round(w, 4)))

        latest = df.iloc[-1]
        direction = int(latest.get("direction", 0))
        direction_str = {1: "做多", -1: "做空", 0: "空仓"}.get(direction, "空仓")
        trade_status = str(latest.get("trade_status", ""))
        return SignalOverview(
            strategy_id="weekend-arb",
            strategy_name=STRATEGY_NAMES["weekend-arb"],
            signal_date=signal_date,
            holdings=holdings,
            signal_detail={
                "direction": direction,
                "direction_str": direction_str,
                "trade_status": trade_status,
                "entry_close": float(latest.get("entry_close", 0)),
                "is_week_last": True,
            },
        )

    # ── csi500-timing ─────────────────────────────────────────

    def _parse_csi500_timing(self) -> SignalOverview | None:
        # Try scheduler output first (latest_signal.json)
        base_dir = os.getenv(
            "CSI500_TIMING_DIR",
            "/Users/xinghuazhang/ygr-project/资产配置监控/实盘_unzip/实盘/ETF实盘代码/data",
        )
        # Check both quant_code and wukong output directories
        candidates = [
            os.path.join(os.getenv("STRATEGY_DATA_DIR", base_dir), "output/csi500_timing/latest_signal.json"),
            # WUKONG: 移植时删除
            "/Users/xinghuazhang/ygr-project/wukong-git/quant_code_product/实盘代码-20260520/实盘代码/output/csi500_timing/latest_signal.json",
        ]
        scheduler_out = None
        for c in candidates:
            c = os.path.normpath(c)
            if os.path.exists(c):
                scheduler_out = c
                break

        if scheduler_out:
            import json
            try:
                with open(scheduler_out) as f:
                    data = json.load(f)
                signal_val = float(data.get("signal", 0))
                weight = min(abs(signal_val), 1.0)
                signal_str = f"仓位{signal_val:.2f}" if signal_val > 0 else "空仓"
                return SignalOverview(
                    strategy_id="csi500-timing",
                    strategy_name=STRATEGY_NAMES["csi500-timing"],
                    signal_date=data.get("date", ""),
                    holdings=[HoldingsItem(
                        ticker="510500.SH",
                        name="中证500",
                        weight=round(weight, 2),
                    )],
                    signal_detail={
                        "signal_value": signal_val,
                        "signal_str": signal_str,
                        "nav": data.get("nav"),
                    },
                )
            except Exception:
                pass

        # Fallback: read raw ETF data file
        data_dir = base_dir
        etf_file = None
        for name in ["512890_SH_etf.csv", "399673_SZ.csv"]:
            p = os.path.join(data_dir, name)
            if os.path.exists(p):
                etf_file = p
                break
        if not etf_file:
            return None
        df = pd.read_csv(etf_file)
        if df.empty or len(df) < 20:
            return None
        last_date = str(df.iloc[-1].iloc[0])
        return SignalOverview(
            strategy_id="csi500-timing",
            strategy_name=STRATEGY_NAMES["csi500-timing"],
            signal_date=last_date[:10] if len(last_date) >= 10 else last_date,
            holdings=[HoldingsItem(
                ticker="510500.SH",
                name="中证500",
                weight=1.0,
            )],
            signal_detail={
                "signal": "等待调度器运行",
                "note": "数据来自静态文件，等待定时任务更新",
            },
        )

    # ── us-fusion ─────────────────────────────────────────────

    def _parse_us_fusion(self) -> SignalOverview | None:
        path = STRATEGY_PATHS["us-fusion"]
        json_file = os.path.join(path, "fusion_daily_signal_latest.json")
        if not os.path.exists(json_file):
            return None
        import json
        with open(json_file) as f:
            data = json.load(f)
        signal_date = data.get("spy_latest_date", "")
        holdings = []
        for h in data.get("complete_holdings", []):
            asset = h.get("asset", "")
            w = h.get("weight", 0)
            if h.get("type") == "CASH":
                continue
            name = _SEC_NAME_MAP.get(asset, asset)
            if h.get("type") == "STOCK":
                name = f"{asset}"
            holdings.append(HoldingsItem(ticker=asset, name=name, weight=w))
        timing = data.get("timing", {})
        return SignalOverview(
            strategy_id="us-fusion",
            strategy_name=STRATEGY_NAMES["us-fusion"],
            signal_date=signal_date,
            holdings=holdings,
            signal_detail={
                "strategy": data.get("strategy", ""),
                "total_exposure": timing.get("total_exposure", 0),
                "volatility": timing.get("volatility", 0),
                "vol_regime": timing.get("vol_regime", ""),
                "base_weights": data.get("base_weights", {}),
            },
        )

    # ── cn-us-hk-timing ───────────────────────────────────────

    def _parse_cn_us_hk_timing(self) -> SignalOverview | None:
        path = STRATEGY_PATHS["cn-us-hk-timing"]
        csv_file = os.path.join(
            path,
            "output_data/index_timing/mas_timing",
            "weight_index_ma_timing_us_hk_cn_mix_0.75_0.25_0.0_0.0_v0.42.csv",
        )
        if not os.path.exists(csv_file):
            return None
        df = pd.read_csv(csv_file, encoding="utf-8-sig")
        if df.empty:
            return None
        latest_date = str(df.iloc[-1]["date"])
        signal_date = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]}"
        latest_rows = df[df["date"] == df["date"].iloc[-1]]
        # Build holdings from CSV data
        seen: dict[str, float] = {}
        for _, row in latest_rows.iterrows():
            code = str(row["windcode"])
            weight = float(row["weight"])
            seen[code] = round(weight, 4)
        # Include all tracked assets, even those with 0 weight
        all_assets = ["SPMO.P", "USMV.BAT", "SETF.HSTECH.HI", "SETF.000300.SH", "SETF.000852.SH"]
        holdings = []
        for code in all_assets:
            w = seen.get(code, 0.0)
            name = _SEC_NAME_MAP.get(code, code)
            holdings.append(HoldingsItem(ticker=code, name=name, weight=w))

        # Compute live current situation from Oracle
        current = self._cn_us_hk_current_situation()

        return SignalOverview(
            strategy_id="cn-us-hk-timing",
            strategy_name=STRATEGY_NAMES["cn-us-hk-timing"],
            signal_date=signal_date,
            holdings=holdings,
            signal_detail={
                "us_alloc": 0.75,
                "hk_alloc": 0.25,
                "cn300_alloc": 0.0,
                "cn1000_alloc": 0.0,
                "current_situation": current,
            },
        )

    # Parameters from index_mas_timing_v0.42.py for each region
    _CN_US_HK_REGIONS = {
        "us": {
            "bench": "SPX.GI",
            "ma_long": [63, 126, 189, 252, 378],
            "ma_short": [5, 10, 15, 20, 40],
            "vol_len": 42,
            "vol_th": 0.19,
        },
        "hk": {
            "bench": "HSTECH.HI",
            "ma_long": [19, 24],
            "ma_short": [20],
            "vol_len": 10,
            "vol_th": 0,
        },
        "cn300": {
            "bench": "000300.SH",
            "ma_long": [25],
            "ma_short": [21],
            "vol_len": 10,
            "vol_th": 0,
        },
        "cn1000": {
            "bench": "000852.SH",
            "ma_long": [10],
            "ma_short": [20],
            "vol_len": 10,
            "vol_th": 0,
        },
    }

    def _cn_us_hk_current_situation(self) -> dict:
        """Compute live momentum timing for each region from Oracle."""
        result = {}
        for region, params in self._CN_US_HK_REGIONS.items():
            try:
                df = self._fetch_index_close(params["bench"], start_date="20230101")
                if df is None or len(df) < 50:
                    result[region] = {"index": params["bench"], "error": "insufficient data"}
                    continue
                prices = pd.Series(df["CLOSE"].values, index=df["TRADE_DATE"].values, dtype=float)
                sig = self._compute_momentum_signal(
                    prices, params["ma_long"], params["ma_short"],
                    params["vol_len"], params["vol_th"],
                )
                if sig:
                    sig["index"] = params["bench"]
                    result[region] = sig
                else:
                    result[region] = {"index": params["bench"], "error": "calculation failed"}
            except Exception as e:
                result[region] = {"index": params["bench"], "error": str(e)}
        return result

    # ── Oracle momentum helpers ──────────────────────────────

    def _fetch_index_close(self, wind_code: str, start_date: str = "20240101") -> pd.DataFrame | None:
        """Fetch index close prices from Oracle for a given WIND code."""
        from app.services.data_service_oracle import oracle_data_service, _init_client, _ORACLE_SCHEMA
        import oracledb

        if not all([oracle_data_service.user, oracle_data_service.password, oracle_data_service.dsn]):
            return None

        _init_client()

        try:
            conn = oracledb.connect(
                user=oracle_data_service.user,
                password=oracle_data_service.password,
                dsn=oracle_data_service.dsn,
            )
        except Exception:
            return None

        try:
            schema = _ORACLE_SCHEMA
            # Try WK_GLOBAL_STOCKS first (covers global indices + some A-share indices)
            sql = f"""
                SELECT TRADE_DT AS trade_date, S_DQ_CLOSE AS close
                FROM {schema}.WK_GLOBAL_STOCKS
                WHERE WIND_CODE = :wind_code
                AND TRADE_DT >= :start_date
                ORDER BY TRADE_DT
            """
            df = pd.read_sql(sql, conn, params={"wind_code": wind_code, "start_date": start_date})
            if df.empty:
                # Fallback to AIndexEODPrices for A-share indices
                sql2 = f"""
                    SELECT TRADE_DT AS trade_date, S_DQ_CLOSE AS close
                    FROM {schema}.AIndexEODPrices
                    WHERE S_INFO_WINDCODE = :wind_code
                    AND TRADE_DT >= :start_date
                    ORDER BY TRADE_DT
                """
                df = pd.read_sql(sql2, conn, params={"wind_code": wind_code, "start_date": start_date})

            if df.empty:
                return None

            df["TRADE_DATE"] = pd.to_datetime(df["TRADE_DATE"], format="%Y%m%d")
            df["CLOSE"] = pd.to_numeric(df["CLOSE"], errors="coerce")
            df = df.dropna(subset=["CLOSE"]).sort_values("TRADE_DATE").reset_index(drop=True)
            return df
        except Exception:
            return None
        finally:
            conn.close()

    def _compute_momentum_signal(
        self,
        prices: pd.Series,
        ma_long: list[int],
        ma_short: list[int],
        vol_len: int,
        vol_th: float,
    ) -> dict | None:
        """Compute momentum timing signal from a price series (dates as index)."""
        needed = max(max(ma_long, default=0), max(ma_short, default=0), vol_len) + 2
        if len(prices) < needed:
            return None

        daily_chg = prices.pct_change()
        vol = daily_chg.rolling(vol_len).std() * np.sqrt(252)
        current_vol = float(vol.iloc[-1])

        mmt_long = {}
        for p in ma_long:
            if len(prices) > p:
                mmt_long[str(p)] = round(float(prices.iloc[-1] / prices.iloc[-p - 1] - 1), 6)

        mmt_short = {}
        for p in ma_short:
            if len(prices) > p:
                mmt_short[str(p)] = round(float(prices.iloc[-1] / prices.iloc[-p - 1] - 1), 6)

        # Base dates for short momentum reference
        base_dates = {}
        for p in ma_short:
            if len(prices) > p:
                base_dates[f"base_date_short_{p}"] = str(prices.index[-p - 1].date()) if hasattr(prices.index[-p - 1], 'date') else str(prices.index[-p - 1])[:10]

        if current_vol < vol_th:
            weight = sum(1 for v in mmt_long.values() if v > 0) / len(mmt_long) if mmt_long else 0
            regime = "long"
        else:
            weight = sum(1 for v in mmt_short.values() if v > 0) / len(mmt_short) if mmt_short else 0
            regime = "short"

        return {
            "close": float(prices.iloc[-1]),
            "date": str(prices.index[-1].date()) if hasattr(prices.index[-1], 'date') else str(prices.index[-1])[:10],
            "daily_chg": round(float(daily_chg.iloc[-1]), 6),
            "volatility": round(current_vol, 4),
            "vol_regime": regime,
            "vol_threshold": vol_th,
            "momentum_long": mmt_long,
            "momentum_short": mmt_short,
            "timing_weight": round(weight, 4),
            **base_dates,
        }

    # ── spmo-usmv-64 ─────────────────────────────────────────

    # Parameters from index_mas_timing_v0.42.py US section
    _SPMO_USMV_PARAMS = {
        "bench": "SPX.GI",
        "ma_long": [63, 126, 189, 252, 378],
        "ma_short": [5, 10, 15, 20, 40],
        "vol_len": 42,
        "vol_th": 0.19,
        "spmo_ratio": 0.6,
        "usmv_ratio": 0.4,
    }

    def _parse_spmo_usmv_64(self) -> SignalOverview | None:
        p = self._SPMO_USMV_PARAMS
        df = self._fetch_index_close(p["bench"], start_date="20230101")
        if df is None or len(df) < 100:
            return None

        prices = pd.Series(df["CLOSE"].values, index=df["TRADE_DATE"].values, dtype=float)
        sig = self._compute_momentum_signal(prices, p["ma_long"], p["ma_short"], p["vol_len"], p["vol_th"])
        if sig is None:
            return None

        w = sig["timing_weight"]
        holdings = [
            HoldingsItem(ticker="SPMO.P", name="美股动量", weight=round(p["spmo_ratio"] * w, 4)),
            HoldingsItem(ticker="USMV.BAT", name="美股低波", weight=round(p["usmv_ratio"] * w, 4)),
        ]

        return SignalOverview(
            strategy_id="spmo-usmv-64",
            strategy_name=STRATEGY_NAMES["spmo-usmv-64"],
            signal_date=sig["date"],
            holdings=holdings,
            signal_detail={
                "bench": p["bench"],
                "close": sig["close"],
                "daily_chg": sig["daily_chg"],
                "volatility": sig["volatility"],
                "vol_regime": sig["vol_regime"],
                "vol_threshold": sig["vol_threshold"],
                "momentum_long": sig["momentum_long"],
                "momentum_short": sig["momentum_short"],
                "timing_weight": sig["timing_weight"],
                "spmo_ratio": p["spmo_ratio"],
                "usmv_ratio": p["usmv_ratio"],
            },
        )

    # ── Generic history for any strategy ──────────────────────

    def get_history(self, strategy_id: str, limit: int = 30) -> list[dict]:
        handler = {
            "weekend-arb": self._history_weekend_arb,
        }.get(strategy_id)
        if handler:
            return handler(limit)
        # Default: return empty list
        return []

    # ── Weekend arb history ───────────────────────────────────

    def _history_weekend_arb(self, limit: int = 50) -> list[dict]:
        path = STRATEGY_PATHS["weekend-arb"]
        csv_file = os.path.join(path, "all_signals_ic_weekend_speculation.csv")
        if not os.path.exists(csv_file):
            return []
        df = pd.read_csv(csv_file, encoding="utf-8-sig")
        if df.empty:
            return []
        df = df.tail(limit)
        results = []
        for _, row in df.iterrows():
            direction = int(row.get("direction", 0))
            results.append({
                "date": str(row["signal_date"]),
                "action": {1: "做多", -1: "做空", 0: "无信号"}.get(direction, "无信号"),
                "detail": {
                    "close": float(row.get("close", 0)),
                    "direction": direction,
                    "trade_status": str(row.get("trade_status", "")),
                    "net_return": float(row.get("net_return", 0)),
                    "ma20_distance": float(row.get("ma20_distance", 0)),
                },
            })
        return results


signal_parser = SignalParser()
