"""
Centralized asset configuration.
Each group is independent — no cross-group mixing.
"""

# ===== US Equities (original + USMV, QQQI, DIVO) =====
US_EQUITIES = {
    "SPY": "S&P 500",
    "VXUS": "Intl ex-US",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000",
    "VOOV": "S&P 500 Value",
    "VOOG": "S&P 500 Growth",
    "VNQ": "Real Estate",
    "COWZ": "Pacer US Cash Cows",
    "USMV": "US Min Vol",
    "QQQI": "Naz 100 Covered Call",
    "DIVO": "Dividend Growers Intl",
}

# ===== US Fixed Income (unchanged) =====
US_FIXED_INCOME = {
    "VGSH": "Short Treasury",
    "AGG": "US Aggregate Bond",
    "TIP": "TIPS",
    "IEF": "7-10yr Treasury",
    "HYG": "High Yield",
    "LQD": "Investment Grade",
    "TLT": "20+yr Treasury",
}

# ===== Commodities & Alts (unchanged) =====
COMMODITIES_ALTS = {
    "GLD": "Gold",
    "PDBC": "Diversified Commodities",
    "USO": "Crude Oil",
    "BTC-USD": "Bitcoin",
}

# ===== US Sector ETFs (SPDR 11 GICS sectors) =====
US_SECTOR_ETFS = {
    "XLB": "Materials",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLK": "Technology",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLC": "Communication Services",
}

# ===== A-Share Equities =====
A_SHARE_EQUITIES = {
    "510050.SH": "上证50ETF",
    "510300.SH": "沪深300ETF",
    "510500.SH": "中证500ETF",
    "512100.SH": "中证1000ETF",
    "563300.SH": "中证2000ETF",
    "159915.SZ": "创业板ETF",
    "159949.SZ": "创业板50ETF",
    "588000.SH": "科创50ETF",
    "510880.SH": "红利ETF",
    "512890.SH": "红利低波ETF",
    "159235.SZ": "中证现金流ETF",
}

# ===== A-Share Industry ETFs =====
A_SHARE_INDUSTRY_ETFS = {
    "512800.SH": "银行ETF",
    "512880.SH": "证券ETF",
    "512070.SH": "非银ETF",
    "159992.SZ": "创新药ETF",
    "512480.SH": "半导体ETF国联安",
    "159995.SZ": "芯片ETF",
    "159555.SZ": "半导体设备ETF",
    "562500.SH": "机器人ETF国泰",
    "561360.SH": "机器人ETF",
    "512660.SH": "军工ETF国泰",
    "515790.SH": "光伏ETF",
    "515030.SH": "新能源车ETF",
    "512690.SH": "白酒ETF",
    "159928.SZ": "消费ETF",
    "512400.SH": "有色金属ETF",
    "516150.SH": "稀土ETF",
    "515230.SH": "钢铁ETF",
    "515220.SH": "煤炭ETF",
    "515880.SH": "通信ETF",
    "515050.SH": "5GETF",
    "512980.SH": "传媒ETF",
    "515000.SH": "科技ETF",
    "512200.SH": "房地产ETF",
    "159766.SZ": "旅游ETF",
    "516110.SH": "汽车ETF",
    "159996.SZ": "家电ETF国泰",
    "516950.SH": "基建ETF",
    "516850.SH": "环保ETF",
}

# ===== A-Share Fixed Income =====
A_SHARE_FIXED_INCOME = {
    "511010.SH": "国债ETF",
    "511260.SH": "信用债ETF",
}

# ===== China Commodities =====
CHINA_COMMODITIES = {
    "518880.SH": "黄金ETF",
    "159985.SZ": "豆粕ETF",
    "159980.SZ": "有色金属ETF",
    "159981.SZ": "能源化工ETF",
}

# ===== Cross-Asset Macro (core multi-asset comparison) =====
CROSS_ASSET_MACRO = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "159915.SZ": "创业板ETF",
    "GLD": "Gold",
    "512890.SH": "红利低波ETF",
    "513520.SH": "日经225ETF",
}

# ===== All Assets (for Cross-Asset Macro self-select) =====
ALL_ASSETS: dict[str, str] = {}
ALL_ASSETS.update(US_EQUITIES)
ALL_ASSETS.update(US_FIXED_INCOME)
ALL_ASSETS.update(COMMODITIES_ALTS)
ALL_ASSETS.update(US_SECTOR_ETFS)
ALL_ASSETS.update(A_SHARE_EQUITIES)
ALL_ASSETS.update(A_SHARE_INDUSTRY_ETFS)
ALL_ASSETS.update(A_SHARE_FIXED_INCOME)
ALL_ASSETS.update(CHINA_COMMODITIES)
ALL_ASSETS.update(CROSS_ASSET_MACRO)

# ===== Asset Groups (for Market Monitor dropdown) =====
ASSET_GROUPS: dict[str, list[str]] = {
    "all": list(ALL_ASSETS.keys()),
    "us_equities": list(US_EQUITIES.keys()),
    "us_fixed_income": list(US_FIXED_INCOME.keys()),
    "commodities_alts": list(COMMODITIES_ALTS.keys()),
    "us_sectors": list(US_SECTOR_ETFS.keys()),
    "a_share_equities": list(A_SHARE_EQUITIES.keys()),
    "a_share_industries": list(A_SHARE_INDUSTRY_ETFS.keys()),
    "a_share_fixed_income": list(A_SHARE_FIXED_INCOME.keys()),
    "china_commodities": list(CHINA_COMMODITIES.keys()),
    "cross_asset_macro": list(CROSS_ASSET_MACRO.keys()),
}

# ===== Ticker → Name mapping (all tickers, two-column display) =====
TICKER_NAMES: dict[str, str] = dict(ALL_ASSETS)