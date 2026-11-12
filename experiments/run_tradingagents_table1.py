"""Run or resume the TradingAgents decision grid for Table 1 tickers."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

TICKERS = ("AAPL", "GOOGL", "AMZN")
START = pd.Timestamp("2024-01-01")
END = pd.Timestamp("2024-03-29")
ANALYSTS = ("market", "social", "news", "fundamentals")


def load_sessions(data_dir: Path) -> list[str]:
    indexes = {}
    for ticker in TICKERS:
        frame = pd.read_csv(data_dir / f"{ticker}.csv", parse_dates=["Date"])
        index = pd.DatetimeIndex(frame["Date"].drop_duplicates().sort_values())
        indexes[ticker] = index
    first = indexes[TICKERS[0]]
    if any(not index.equals(first) for index in indexes.values()):
        raise ValueError("Table 1 ticker date indexes do not match")
    sessions = first[(first >= START) & (first <= END)]
    if len(sessions) != 61:
        raise ValueError(f"expected 61 paper-window sessions; found {len(sessions)}")
    return [date.strftime("%Y-%m-%d") for date in sessions]


def _entry_rows(entries: list[dict]) -> pd.DataFrame:
    columns = ["date", "ticker", "rating", "decision", "pending", "raw_return", "alpha", "holding", "resolved"]
    return pd.DataFrame([{key: entry.get(key) for key in columns} for entry in entries], columns=columns)


def run(data_dir: Path, output_dir: Path, run_id: str, pilot: bool) -> dict:
    from tradingagents.backtest import run_backtest
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.memory import TradingMemoryLog

    dates = load_sessions(data_dir)
    selected_dates = dates[-1:] if pilot else dates
    expected = {(ticker, date) for ticker in TICKERS for date in selected_dates}
    output_dir.mkdir(parents=True, exist_ok=True)
    run_store = output_dir / "run_files"
    config = DEFAULT_CONFIG.copy()
    config["results_dir"] = str(run_store / "results")
    config["data_cache_dir"] = str(run_store / "cache")
    config["memory_log_path"] = str(run_store / "memory" / "unused.md")

    logging.getLogger("tradingagents.backtest").setLevel(logging.ERROR)

    def progress(done: int, total: int, ticker: str, date: str) -> None:
        print(f"[{done}/{total}] {ticker} {date}", flush=True)

    result = run_backtest(
        list(TICKERS), selected_dates, config,
        selected_analysts=ANALYSTS, run_id=run_id, progress=progress,
    )
    entries = TradingMemoryLog({"memory_log_path": str(result.log_path)}).load_entries()
    stored = {(entry["ticker"], entry["date"]) for entry in entries}
    missing = sorted(expected - stored)
    rows = _entry_rows(entries).sort_values(["date", "ticker"])
    rows.to_csv(output_dir / "decision_cells.csv", index=False)

    run_settings = None
    for ticker, date in sorted(stored & expected):
        state_path = (
            run_store / "results" / "backtest" / run_id / ticker
            / "TradingAgentsStrategy_logs" / f"full_states_log_{date}.json"
        )
        if state_path.exists():
            run_settings = json.loads(state_path.read_text(encoding="utf-8")).get("run_settings")
            break

    status = {
        "run_id": run_id,
        "phase": "pilot" if pilot else "full",
        "expected_cells": len(expected),
        "stored_cells_in_phase": len(expected & stored),
        "cells_run": result.cells_run,
        "cells_skipped": result.skipped,
        "missing_cells": [{"ticker": ticker, "date": date} for ticker, date in missing],
        "failures": [
            {"ticker": ticker, "date": date, "failure": "cell failed"}
            for ticker, date, _message in result.failures
        ],
        "settlement_failure_count": len(result.settlement_failures),
        "memory_log": str(result.log_path),
        "run_settings": run_settings,
    }
    status_name = "pilot_status.json" if pilot else "run_status.json"
    (output_dir / status_name).write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps({key: status[key] for key in (
        "phase", "expected_cells", "stored_cells_in_phase", "cells_run", "cells_skipped",
        "missing_cells", "settlement_failure_count",
    )}, indent=2))
    return status


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=root / "smoke_test" / "paper_prices")
    parser.add_argument("--output-dir", type=Path, default=root / "smoke_test" / "table1_agent_full")
    parser.add_argument("--run-id", default="table1_2024")
    parser.add_argument("--pilot", action="store_true", help="Run the final paper-window session only")
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    status = run(args.data_dir, output_dir, args.run_id, args.pilot)
    if status["missing_cells"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
