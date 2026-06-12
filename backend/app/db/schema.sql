-- asset-monitor schema (idempotent, safe to run on every startup)

CREATE TABLE IF NOT EXISTS price_daily (
    ticker       TEXT NOT NULL,
    trade_date   DATE NOT NULL,
    close        DOUBLE PRECISION NOT NULL,
    source       TEXT,
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ticker, trade_date)
);

CREATE TABLE IF NOT EXISTS compute_cache (
    cache_key    TEXT PRIMARY KEY,
    data_type    TEXT NOT NULL,
    price_hash   TEXT NOT NULL,
    dates        JSONB NOT NULL,
    values       JSONB NOT NULL,
    row_count    INTEGER NOT NULL,
    computed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS signal_history (
    id           SERIAL PRIMARY KEY,
    strategy_id  TEXT NOT NULL,
    signal_date  DATE NOT NULL,
    holdings     JSONB NOT NULL,
    signal_detail JSONB,
    captured_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(strategy_id, signal_date)
);

CREATE TABLE IF NOT EXISTS backtest_result (
    strategy_id    TEXT NOT NULL,
    snapshot_date  DATE NOT NULL,
    nav_curve      JSONB NOT NULL,
    metrics        JSONB,
    data_hash      TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (strategy_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_price_ticker_date ON price_daily(ticker, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_signal_strategy_date ON signal_history(strategy_id, signal_date DESC);
CREATE INDEX IF NOT EXISTS idx_compute_data_type ON compute_cache(data_type);
