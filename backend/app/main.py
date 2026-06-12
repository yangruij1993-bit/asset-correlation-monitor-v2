from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
import os

from app.routers import analysis, frontier, signals
from app.services.data_service import data_service

SCHEDULER_ENABLED = os.getenv("STRATEGY_SCHEDULER", "false").lower() == "true" and bool(os.getenv("STRATEGY_DATA_DIR"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Asset Correlation Monitor API started")
    # 1. PostgreSQL
    from app.db import create_pool, init_db, close_pool
    await create_pool()
    await init_db()
    # 2. Price data (PG primary, CSV fallback)
    await data_service.ensure_data()
    # 3. Warm GARCH/Kalman from PG cache (or compute + persist)
    from app.services.analysis_service import analysis_service
    loaded = await analysis_service.warm_from_cache()
    if not loaded:
        print("PG cache empty/stale, computing GARCH/Kalman...")
        import asyncio
        analysis_service._ensure_garch()
        analysis_service._ensure_kalman()
        await analysis_service._persist_garch()
        await analysis_service._persist_kalman()
        print("GARCH/Kalman computed and persisted to PG")
    # 4. Scheduler
    if SCHEDULER_ENABLED:
        from app.services.strategy_scheduler import start_scheduler
        start_scheduler()
    yield
    if SCHEDULER_ENABLED:
        from app.services.strategy_scheduler import stop_scheduler
        stop_scheduler()
    await close_pool()
    print("Asset Correlation Monitor API shutdown")


app = FastAPI(
    title="Asset Correlation Monitor API",
    description="ETF Correlation and Asset Allocation Monitor",
    version="1.0.0",
    lifespan=lifespan,
)

cors_origins = os.getenv("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins.split(",") if cors_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router)
app.include_router(frontier.router)
app.include_router(signals.router)

# Serve frontend static files (after API routes so /api/* takes priority)
_frontend_dist = Path(__file__).parent.parent / "frontend" / "out"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")


@app.get("/")
async def root():
    return {"status": "running", "service": "Asset Correlation Monitor API"}


@app.get("/api/v1/health")
async def health():
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
