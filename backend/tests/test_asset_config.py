import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _literal_dict_from_assignment(path: Path, name: str) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in {path}")


class AssetConfigTest(unittest.TestCase):
    def test_spmo_is_configured_with_usmv_across_backend_and_frontend(self):
        assets_py = ROOT / "backend" / "app" / "config" / "assets.py"
        oracle_py = ROOT / "backend" / "app" / "services" / "data_service_oracle.py"
        labels_ts = ROOT / "frontend" / "src" / "lib" / "labels.ts"

        us_equities = _literal_dict_from_assignment(assets_py, "US_EQUITIES")
        oracle_map = _literal_dict_from_assignment(oracle_py, "US_TICKER_TO_ORACLE")
        labels = labels_ts.read_text(encoding="utf-8")

        self.assertIn("USMV", us_equities)
        self.assertIn("SPMO", us_equities)
        self.assertEqual(us_equities["SPMO"], "S&P 500 Momentum")
        self.assertLess(list(us_equities).index("USMV"), list(us_equities).index("SPMO"))

        self.assertEqual(oracle_map["SPMO"], "SPMO.P")

        all_assets_match = re.search(r"export const ALL_ASSET_TICKERS = \[(.*?)\];", labels, re.S)
        self.assertIsNotNone(all_assets_match)
        all_assets_block = all_assets_match.group(1)
        self.assertLess(all_assets_block.index('"USMV"'), all_assets_block.index('"SPMO"'))

        self.assertIn('SPMO: "S&P 500 Momentum"', labels)


if __name__ == "__main__":
    unittest.main()
