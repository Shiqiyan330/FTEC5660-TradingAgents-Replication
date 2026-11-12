"""Tests for mapping dated model ratings to long-only target weights."""

import unittest

import pandas as pd

from experiments.score_tradingagents_table1 import build_targets


class TradingAgentsTable1Tests(unittest.TestCase):
    def test_hold_and_review_retain_the_last_target(self):
        dates = pd.date_range("2024-01-02", periods=5, freq="B")
        entries = pd.DataFrame([
            {"date": dates[0].strftime("%Y-%m-%d"), "ticker": "AAPL", "rating": "Buy", "decision": "buy"},
            {"date": dates[1].strftime("%Y-%m-%d"), "ticker": "AAPL", "rating": "Hold", "decision": "hold"},
            {"date": dates[2].strftime("%Y-%m-%d"), "ticker": "AAPL", "rating": "Underweight", "decision": "reduce"},
            {"date": dates[3].strftime("%Y-%m-%d"), "ticker": "AAPL", "rating": "REVIEW", "decision": "review"},
            {"date": dates[4].strftime("%Y-%m-%d"), "ticker": "AAPL", "rating": "Sell", "decision": "sell"},
        ])

        targets, missing = build_targets(entries, "AAPL", dates)

        self.assertEqual(missing, [])
        self.assertEqual(targets["target_weight"].tolist(), [1.0, 1.0, 0.5, 0.5, 0.0])

    def test_missing_decision_is_review_and_is_reported(self):
        dates = pd.date_range("2024-01-02", periods=2, freq="B")
        entries = pd.DataFrame([
            {"date": dates[0].strftime("%Y-%m-%d"), "ticker": "AAPL", "rating": "Overweight", "decision": ""},
        ])

        targets, missing = build_targets(entries, "AAPL", dates)

        self.assertEqual(missing, [dates[1].strftime("%Y-%m-%d")])
        self.assertEqual(targets["rating"].tolist(), ["Overweight", "REVIEW"])
        self.assertEqual(targets["target_weight"].tolist(), [0.75, 0.75])


if __name__ == "__main__":
    unittest.main()
