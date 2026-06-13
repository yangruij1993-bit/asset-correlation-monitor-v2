import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from app.services.data_service import DataService


class DataServiceRefreshTest(unittest.TestCase):
    def test_pg_data_refreshes_when_configured_ticker_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = DataService()
            service.cache_dir = Path(tmp)
            service.prices_file = Path(tmp) / "prices.csv"

            today = pd.Timestamp.today().normalize()

            async def load_from_pg():
                return pd.DataFrame({"USMV": [100.0]}, index=[today])

            service._load_from_pg = load_from_pg

            refreshed = {"called": False}

            def refresh_data():
                refreshed["called"] = True
                return pd.DataFrame({"SPMO": [50.0]}, index=[today])

            service.refresh_data = refresh_data

            async def persist_to_pg(df, source="refresh"):
                return None

            service._persist_to_pg = persist_to_pg

            with patch("app.services.data_service.ALL_ASSETS", {"USMV": "US Min Vol", "SPMO": "S&P 500 Momentum"}):
                asyncio.run(service.ensure_data())

            self.assertTrue(refreshed["called"])


if __name__ == "__main__":
    unittest.main()
