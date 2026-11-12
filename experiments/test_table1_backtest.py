"""Focused tests for the standalone Table 1 reproduction runner."""

import unittest

import pandas as pd

from experiments.table1_backtest import (
    INITIAL_CASH,
    score_portfolio,
    simulate,
    target_for_rating,
    targets_for_execution,
)


class Table1BacktestTests(unittest.TestCase):
    def test_close_signal_is_filled_at_the_next_session_open(self):
        dates = pd.date_range("2024-01-02", periods=3, freq="B")
        signal = pd.Series([1.0, 0.0, 1.0], index=dates)

        target = targets_for_execution(signal, dates)

        self.assertEqual(target.tolist(), [0.0, 1.0, 0.0])

    def test_rating_mapping_preserves_hold_and_review_positions(self):
        self.assertEqual(target_for_rating("Buy", 0.2), 1.0)
        self.assertEqual(target_for_rating("Overweight", 0.2), 0.75)
        self.assertEqual(target_for_rating("Underweight", 0.8), 0.50)
        self.assertEqual(target_for_rating("Sell", 0.8), 0.0)
        self.assertEqual(target_for_rating("Hold", 0.4), 0.4)
        self.assertEqual(target_for_rating("REVIEW", 0.4), 0.4)

    def test_market_order_costs_reduce_portfolio_value(self):
        dates = pd.date_range("2024-01-02", periods=4, freq="B")
        close = pd.Series([100.0, 102.0, 101.0, 104.0], index=dates)
        open_ = pd.Series([99.0, 101.0, 100.0, 103.0], index=dates)
        target = pd.Series([1.0, 1.0, 0.0, 0.0], index=dates)
        risk_free = pd.Series(0.0, index=dates)

        free = simulate(close, open_, target, commission_bps=0.0, slippage_bps=0.0)
        costed = simulate(close, open_, target, commission_bps=1.0, slippage_bps=5.0)

        self.assertLess(costed.final_value(), free.final_value())
        score = score_portfolio(costed, risk_free)
        self.assertGreaterEqual(score["mdd_pct"], 0.0)
        self.assertNotEqual(score["final_value"], INITIAL_CASH)

    def test_flat_portfolio_reports_zero_drawdown(self):
        dates = pd.date_range("2024-01-02", periods=3, freq="B")
        prices = pd.Series([100.0, 100.0, 100.0], index=dates)
        flat = pd.Series(0.0, index=dates)

        portfolio = simulate(prices, prices, flat)

        self.assertEqual(score_portfolio(portfolio, flat)["mdd_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
