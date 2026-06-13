export function tickerDisplay(ticker: string): string {
  return TICKER_DEFINITIONS[ticker] || ticker;
}

function _isUsTicker(ticker: string): boolean {
  return !ticker.includes(".");
}

function _lookupAshareName(ticker: string): string | undefined {
  return TICKER_DEFINITIONS[ticker] ?? TICKER_DEFINITIONS[ticker + ".SH"] ?? TICKER_DEFINITIONS[ticker + ".SZ"];
}

/** US tickers: code only. A-share tickers: name only */
export function heatmapDisplay(ticker: string): string {
  if (_isUsTicker(ticker)) {
    // Might be a 6-digit A-share code without suffix
    if (/^\d{6}$/.test(ticker)) return _lookupAshareName(ticker) || ticker;
    return ticker;
  }
  return _lookupAshareName(ticker) || ticker;
}

export const ALL_ASSET_TICKERS = [
  // US Equities
  "SPY", "VXUS", "QQQ", "IWM", "VOOV", "VOOG", "VNQ", "COWZ", "USMV", "SPMO", "QQQI", "DIVO",
  // US Fixed Income
  "VGSH", "AGG", "TIP", "IEF", "HYG", "LQD", "TLT",
  // Commodities & Alts
  "GLD", "PDBC", "USO", "BTC-USD",
  // US Sector ETFs
  "XLB", "XLE", "XLF", "XLI", "XLK", "XLRE", "XLU", "XLV", "XLY", "XLP", "XLC",
  // A-Share Equities
  "510050.SH", "510300.SH", "510500.SH", "512100.SH", "563300.SH", "159915.SZ", "159949.SZ",
  "588000.SH", "510880.SH", "512890.SH", "159235.SZ",
  // A-Share Industry ETFs
  "512800.SH", "512880.SH", "512070.SH", "159992.SZ", "512480.SH", "159995.SZ",
  "159555.SZ", "562500.SH", "561360.SH", "512660.SH", "515790.SH", "515030.SH",
  "512690.SH", "159928.SZ", "512400.SH", "516150.SH", "515230.SH", "515220.SH",
  "515880.SH", "515050.SH", "512980.SH", "515000.SH", "512200.SH", "159766.SZ",
  "516110.SH", "159996.SZ", "516950.SH", "516850.SH",
  // A-Share Fixed Income
  "511010.SH", "511260.SH",
  // China Commodities
  "518880.SH", "159985.SZ", "159980.SZ", "159981.SZ",
  // Cross-Asset Macro
  "SPY", "513520.SH",
];

export const TICKER_DEFINITIONS: Record<string, string> = {
  // US Equities
  VXUS: "Intl ex-US",
  QQQ: "Nasdaq 100",
  IWM: "Russell 2000",
  VOOV: "S&P 500 Value",
  VOOG: "S&P 500 Growth",
  VNQ: "Real Estate",
  COWZ: "Pacer US Cash Cows",
  USMV: "US Min Vol",
  SPMO: "S&P 500 Momentum",
  QQQI: "Naz 100 Covered Call",
  DIVO: "Dividend Growers Intl",
  SPY: "SPDR S&P 500",
  // US Fixed Income
  VGSH: "Short Treasury",
  AGG: "US Aggregate Bond",
  TIP: "TIPS",
  IEF: "7-10yr Treasury",
  HYG: "High Yield",
  LQD: "Investment Grade",
  TLT: "20+yr Treasury",
  // Commodities & Alts
  GLD: "Gold",
  PDBC: "Diversified Commodities",
  USO: "Crude Oil",
  "BTC-USD": "Bitcoin",
  // US Sector ETFs
  XLB: "Materials",
  XLE: "Energy",
  XLF: "Financials",
  XLI: "Industrials",
  XLK: "Technology",
  XLRE: "Real Estate",
  XLU: "Utilities",
  XLV: "Health Care",
  XLY: "Consumer Discretionary",
  XLP: "Consumer Staples",
  XLC: "Communication Services",
  // Cross-Asset Macro
  "513520.SH": "日经225",
  // A-Share Equities
  "510050.SH": "上证50",
  "510300.SH": "沪深300",
  "510500.SH": "中证500",
  "512100.SH": "中证1000",
  "563300.SH": "中证2000",
  "159915.SZ": "创业板",
  "159949.SZ": "创业板50",
  "588000.SH": "科创50",
  "510880.SH": "红利",
  "512890.SH": "红利低波",
  "159235.SZ": "中证现金流",
  // A-Share Industry ETFs
  "512800.SH": "银行",
  "512880.SH": "证券",
  "512070.SH": "非银",
  "159992.SZ": "创新药",
  "512480.SH": "半导体国联安",
  "159995.SZ": "芯片",
  "159555.SZ": "半导体设备",
  "562500.SH": "机器人国泰",
  "561360.SH": "机器人",
  "512660.SH": "军工国泰",
  "515790.SH": "光伏",
  "515030.SH": "新能源车",
  "512690.SH": "白酒",
  "159928.SZ": "消费",
  "512400.SH": "有色金属",
  "516150.SH": "稀土",
  "515230.SH": "钢铁",
  "515220.SH": "煤炭",
  "515880.SH": "通信",
  "515050.SH": "5G",
  "512980.SH": "传媒",
  "515000.SH": "科技",
  "512200.SH": "房地产",
  "159766.SZ": "旅游",
  "516110.SH": "汽车",
  "159996.SZ": "家电国泰",
  "516950.SH": "基建",
  "516850.SH": "环保",
  // A-Share Fixed Income
  "511010.SH": "国债",
  "511260.SH": "信用债",
  // China Commodities
  "518880.SH": "黄金",
  "159985.SZ": "豆粕",
  "159980.SZ": "有色金属",
  "159981.SZ": "能源化工",
};

const TICKER_DEF_KEYS = Object.keys(TICKER_DEFINITIONS).sort((a, b) => b.length - a.length);

export function pairDefinitions(pair: string): string {
  const found: string[] = [];
  let remaining = pair;
  for (const key of TICKER_DEF_KEYS) {
    if (remaining.includes(key)) {
      found.push(TICKER_DEFINITIONS[key]);
      remaining = remaining.replace(key, "");
    }
  }
  return found.join(" / ") || pair;
}

export const ASSET_GROUP_LABELS: Record<string, string> = {
  all: "All Assets",
  us_equities: "US Equities",
  us_fixed_income: "US Fixed Income",
  commodities_alts: "Commodities & Alts",
  us_sectors: "US Sectors",
  a_share_equities: "A-Share Equities",
  a_share_industries: "A-Share Industries",
  a_share_fixed_income: "A-Share Fixed Income",
  china_commodities: "China Commodities",
  cross_asset_macro: "Cross-Asset Macro",
};
