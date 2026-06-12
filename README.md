# Asset Correlation Monitor

A web-based macroeconomic asset allocation and correlation monitor. Tracks **60+ assets** across US equities, US fixed income, A-share ETFs, and commodities, calculating dynamic correlations (GARCH + Kalman Filter) and detecting anomaly signals (Z-scores) to guide portfolio allocation.

## Architecture

*   **Backend**: Python, FastAPI, Pandas, Tushare, yfinance, PostgreSQL
*   **Frontend**: Next.js 14, React, Tailwind CSS, Recharts, Plotly.js (static export)
*   **Data**: A-share ETFs via Tushare, US ETFs via Oracle/yfinance, persisted in PostgreSQL with CSV fallback.

## Features

*   **Hierarchical Group Navigation**: Two-tier tabs — switch between 4 macro groups, then drill into Overview / Time Series / Insights.
*   **Dynamic Correlation (Kalman Filter)**: Replaces standard rolling windows with a GARCH(1,1) + 1D Kalman Filter (random walk) algorithm to eliminate "ghost effects", offering 3 sensitivity tiers (Fast / Standard / Smooth).
*   **Efficient Frontier Optimizer**: A standalone sandbox to run Markowitz mean-variance optimization across all 19 assets using the latest Smooth Kalman covariance matrix. Features Max Sharpe, Min Vol, and editable forward estimates with localStorage persistence.
*   **Overview Dashboard**: Summary statistics (CAGR, Vol, Max DD) and Correlation Heatmaps (Fast vs Smooth sensitivities), sorted by historical volatility within each group.
*   **Rolling Correlation Time Series**: Select a base asset to view its dynamic correlation with all other assets simultaneously.
*   **Anomaly Signals**: Z-Score based alerting for ETF pairs diverging from historical norms.
*   **Strategy Signal Plugin**: Drop a JSON file into `strategies/` to plug in any strategy's signals, holdings, and NAV curve. No backend code changes needed. See [STRATEGIES.md](STRATEGIES.md) for the spec.
*   **Insights Panel**: Auto-generated regime notes and allocation suggestions based on current correlations.
*   **Custom Hover Tooltips**: Hovering over tickers in Summary, Forward Table, Custom Portfolio, and Anomaly Signals shows full asset definitions (e.g. "BTC" → "Bitcoin (USD)").

## Recent Fixes

*   **Time Series date alignment**: Fixed a bug where `iloc` positional sampling caused BTC-USD (weekend data) and ETFs (trading days only) to produce disjoint date sets, resulting in invisible lines on the Rolling Time Series chart. Now samples from the union of all dates so all series share the same x-axis.
*   **Ticker hover definitions**: Replaced native `title` attribute (unreliable on macOS) with custom styled React tooltips across all table components.

## Local Setup

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env  # fill in your TUSHARE_TOKEN and DATABASE_URL
```

PostgreSQL setup:

```sql
CREATE DATABASE asset_monitor;
CREATE USER assetmon WITH PASSWORD 'assetmon';
GRANT ALL PRIVILEGES ON DATABASE asset_monitor TO assetmon;
```

### 2. Frontend

```bash
cd frontend
npm install
```

## Running Locally

You can start both the backend and frontend simultaneously using the provided script:

```bash
chmod +x start.sh
./start.sh
```

Or run them individually:

**Backend:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --port 8012
```

**Frontend:**
```bash
cd frontend
npm run dev -- -p 3012
```

Open [http://localhost:3012](http://localhost:3012) in your browser.

## Sharing via ngrok

One tunnel is enough — the backend also serves the built frontend:

```bash
ngrok http 8012
# Get URL like https://xxxx.ngrok-free.app
cd frontend
NEXT_PUBLIC_API_URL=https://xxxx.ngrok-free.app/api/v1/analysis npx next build
# Restart backend — it serves frontend/out/ as static files
```
