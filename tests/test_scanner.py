import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from scanner import analyze, percentage


class ScannerTests(unittest.TestCase):
    @staticmethod
    def bars(slope=0.1, spike=4):
        return [
            {"date": "2025-%03d" % i, "close": 10 + slope * i,
             "volume": 1000 * (spike if i == 229 else 1)}
            for i in range(230)
        ]

    def test_breakout_and_score(self):
        result = analyze("DEMO", self.bars())
        self.assertEqual(result["signal"], "Breakout candidate")
        self.assertTrue(result["above_50d"])
        self.assertEqual(result["relative_volume"], 4)
        self.assertTrue(0 <= result["score"] <= 100)

    def test_flat_market_is_not_breakout(self):
        result = analyze("DEMO", self.bars(0, 1))
        self.assertEqual(result["return_1m"], 0)
        self.assertEqual(result["signal"], "Monitor")

    def test_short_history_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze("DEMO", self.bars()[:80])

    def test_zero_division(self):
        self.assertIsNone(percentage(100, 0))


if __name__ == "__main__":
    unittest.main()
