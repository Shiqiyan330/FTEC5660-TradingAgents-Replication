"""Tests for ticker-parallel Table 1 execution and its date barrier."""

import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from experiments.run_tradingagents_table1 import (
    _news_unavailable_sources,
    _retry_status,
    _run_parallel_backtest,
)


class _MemoryLog:
    def load_entries(self):
        return [{"ticker": "AAPL", "date": "2024-01-02"}]


class _Tracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.barriers = {
            "2024-01-02": threading.Barrier(2),
            "2024-01-03": threading.Barrier(3),
        }
        self.active = {}
        self.max_active = {}
        self.completed = {}
        self.violations = []

    def run(self, ticker, date):
        with self.lock:
            if date == "2024-01-03" and self.completed.get("2024-01-02", 0) != 2:
                self.violations.append("next date started before prior date completed")
            self.active[date] = self.active.get(date, 0) + 1
            self.max_active[date] = max(self.max_active.get(date, 0), self.active[date])
        self.barriers[date].wait(timeout=3)
        time.sleep(0.01)
        with self.lock:
            self.active[date] -= 1
            self.completed[date] = self.completed.get(date, 0) + 1


class _FakeGraph:
    def __init__(self, tracker):
        self.tracker = tracker
        self.memory_log = _MemoryLog()

    def propagate(self, ticker, date):
        self.tracker.run(ticker, date)

    def settle_pending(self, ticker):
        return SimpleNamespace(failed=[])


class ParallelTable1Tests(unittest.TestCase):
    def test_news_audit_distinguishes_unavailable_from_empty_window(self):
        self.assertEqual(
            _news_unavailable_sources(
                "AAPL-specific and global-news feeds were unavailable for this window.",
                "AAPL",
            ),
            (True, True),
        )
        self.assertEqual(
            _news_unavailable_sources("No news found for AAPL in this window.", "AAPL"),
            (False, False),
        )
        self.assertEqual(_retry_status("Yahoo Finance news unavailable"), "still_unavailable")
        self.assertEqual(_retry_status("No news found between dates"), "query_succeeded_no_articles")
        self.assertEqual(_retry_status("## AAPL News\n\nHeadline"), "recovered_articles")

    def test_tickers_overlap_and_dates_wait_for_a_barrier(self):
        tracker = _Tracker()

        def graph_factory(_analysts, config):
            self.assertTrue(Path(config["memory_log_path"]).is_file() or
                            Path(config["memory_log_path"]).parent.is_dir())
            return _FakeGraph(tracker)

        project_root = Path(__file__).resolve().parents[1]
        results_dir = project_root / "smoke_test" / "table1_agent_full" / "config_check" / "results"
        run_id = f"parallel-unit-{uuid4().hex[:10]}"
        run_dir = results_dir / "backtest" / run_id
        try:
            result = _run_parallel_backtest(
                ["AAPL", "GOOGL", "AMZN"],
                ["2024-01-02", "2024-01-03"],
                {"results_dir": str(results_dir)},
                run_id=run_id,
                graph_factory=graph_factory,
            )
        finally:
            if run_dir.is_dir():
                import shutil
                shutil.rmtree(run_dir)

        self.assertEqual(result.cells_run, 5)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.failures, [])
        self.assertEqual(tracker.violations, [])
        self.assertEqual(tracker.max_active["2024-01-02"], 2)
        self.assertEqual(tracker.max_active["2024-01-03"], 3)


if __name__ == "__main__":
    unittest.main()
