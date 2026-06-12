import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://assetmon:assetmon@localhost:5432/asset_monitor",
)
