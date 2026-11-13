"""Run or resume the TradingAgents decision grid for Table 1 tickers."""

from __future__ import annotations

import argparse
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

TICKERS = ("AAPL", "GOOGL", "AMZN")
START = pd.Timestamp("2024-01-01")
END = pd.Timestamp("2024-03-29")
ANALYSTS = ("market", "social", "news", "fundamentals")
logger = logging.getLogger(__name__)


def _run_parallel_backtest(
    tickers: list[str],
    dates: list[str],
    config: dict,
    selected_analysts=ANALYSTS,
    run_id: str | None = None,
    progress=None,
    graph_factory=None,
):
    """Run same-date ticker decisions concurrently, with a barrier before the next date."""
    from tradingagents.backtest import BacktestResult
    from tradingagents.dataflows.symbols import safe_ticker_component

    if graph_factory is None:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        graph_factory = TradingAgentsGraph

    tickers = list(dict.fromkeys(tickers))
    dates = list(dict.fromkeys(dates))
    if not tickers:
        raise ValueError("at least one ticker is required")
    run_id = safe_ticker_component(run_id) if run_id else None
    runs = Path(config["results_dir"]) / "backtest"
    if run_id:
        (runs / run_id).mkdir(parents=True, exist_ok=True)
    else:
        from tradingagents.backtest import _new_run
        run_id = _new_run(runs)
    run_dir = runs / run_id
    run_config = {
        **config,
        "results_dir": str(run_dir),
        "memory_log_path": str(run_dir / "trading_memory.md"),
    }
    graphs = {
        ticker: graph_factory(selected_analysts, config=run_config)
        for ticker in tickers
    }
    log_path = Path(run_config["memory_log_path"])
    result = BacktestResult(run_id=run_id, log_path=log_path)
    done = {(entry["ticker"], entry["date"])
            for entry in graphs[tickers[0]].memory_log.load_entries()}
    cells = [(ticker, date) for date in dates for ticker in tickers]
    todo = [cell for cell in cells if cell not in done]
    todo_set = set(todo)
    result.skipped = len(cells) - len(todo)

    # A date barrier keeps cross-ticker memory point-in-time consistent while
    # overlapping each ticker's independent LLM and data-provider waits.
    with ThreadPoolExecutor(max_workers=len(tickers)) as executor:
        submitted = 0
        for date in dates:
            batch = [(ticker, date) for ticker in tickers if (ticker, date) in todo_set]
            futures = {}
            for ticker, cell_date in batch:
                submitted += 1
                if progress:
                    progress(submitted, len(todo), ticker, cell_date)
                futures[executor.submit(graphs[ticker].propagate, ticker, cell_date)] = (ticker, cell_date)
            for future in as_completed(futures):
                ticker, cell_date = futures[future]
                try:
                    future.result()
                    result.cells_run += 1
                except Exception as exc:
                    logger.warning("Backtest cell %s %s failed: %s", ticker, cell_date, exc)
                    result.failures.append((ticker, cell_date, str(exc)))

    for ticker in tickers:
        try:
            settled = graphs[ticker].settle_pending(ticker)
            result.settlement_failures.extend(
                (failed_ticker, f"{date}: {reason}")
                for failed_ticker, date, reason in settled.failed
            )
        except Exception as exc:
            logger.warning("Settling %s failed: %s", ticker, exc)
            result.settlement_failures.append((ticker, str(exc)))
    return result


def _news_unavailable_sources(report: str, ticker: str) -> tuple[bool, bool]:
    """Return company/global news gaps explicitly described in an agent report."""
    text = report.lower()
    unavailable = any(marker in text for marker in (
        "unavailable", "data_unavailable", "could not return", "failed to fetch",
    ))
    if not unavailable:
        return False, False
    company = any(marker in text for marker in (
        "company news", "company-news", "ticker-specific", f"{ticker.lower()}-specific",
    ))
    global_news = any(marker in text for marker in (
        "global news", "global-news", "global feed", "global-news feed",
    ))
    if not company and not global_news:
        company = True
    return company, global_news


def _retry_status(text: str) -> str:
    """Classify a Yahoo response without confusing a valid empty window with failure."""
    value = text.lower()
    if any(marker in value for marker in ("data_unavailable", "unavailable", "failed")):
        return "still_unavailable"
    if "no news found" in value or "no articles" in value:
        return "query_succeeded_no_articles"
    if "## " in text:
        return "recovered_articles"
    return "response_received"


def _audit_and_retry_news(
    output_dir: Path,
    run_store: Path,
    run_id: str,
    tickers: list[str],
    dates: list[str],
    config: dict,
) -> dict:
    """Audit saved news reports, then retry only Yahoo sources reported unavailable."""
    from tradingagents.agents.analysts.sentiment_analyst import _seven_days_back
    from tradingagents.dataflows.config import run_config
    from tradingagents.dataflows.vendors.yahoo.news import (
        get_global_news_yfinance,
        get_news_yfinance,
    )

    run_dir = run_store / "results" / "backtest" / run_id
    audit_rows, targets = [], set()
    for date in dates:
        for ticker in tickers:
            state_path = (
                run_dir / ticker / "TradingAgentsStrategy_logs"
                / f"full_states_log_{date}.json"
            )
            if not state_path.exists():
                audit_rows.append({
                    "ticker": ticker, "date": date, "state_status": "missing_state",
                    "company_news": "not_checked", "global_news": "not_checked",
                })
                continue
            state = json.loads(state_path.read_text(encoding="utf-8"))
            report = str(state.get("news_report") or "")
            company_missing, global_missing = _news_unavailable_sources(report, ticker)
            audit_rows.append({
                "ticker": ticker,
                "date": date,
                "state_status": "present",
                "company_news": "unavailable" if company_missing else "no_unavailability_reported",
                "global_news": "unavailable" if global_missing else "no_unavailability_reported",
            })
            if company_missing:
                targets.add(("company", ticker, date))
            if global_missing:
                targets.add(("global", "", date))

    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(audit_rows).to_csv(output_dir / "news_coverage_audit.csv", index=False)
    retry_dir = output_dir / "news_retries"
    retry_dir.mkdir(parents=True, exist_ok=True)

    def result_path(target):
        source, ticker, date = target
        name = f"{ticker or 'GLOBAL'}__{date}__{source}.json"
        return retry_dir / name

    pending = [target for target in sorted(targets) if not result_path(target).exists()]

    def fetch(target):
        source, ticker, date = target
        with run_config(config):
            try:
                if source == "company":
                    text = get_news_yfinance(ticker, _seven_days_back(date), date)
                else:
                    text = get_global_news_yfinance(date)
                status = _retry_status(str(text))
                return {
                    "source": source,
                    "ticker": ticker or "GLOBAL",
                    "date": date,
                    "status": status,
                    "result_text": str(text),
                }
            except Exception as exc:
                return {
                    "source": source,
                    "ticker": ticker or "GLOBAL",
                    "date": date,
                    "status": "request_failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }

    with ThreadPoolExecutor(max_workers=max(1, min(3, len(tickers)))) as executor:
        futures = {executor.submit(fetch, target): target for target in pending}
        for future in as_completed(futures):
            target = futures[future]
            record = future.result()
            result_path(target).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    records = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(retry_dir.glob("*.json"))]
    pd.DataFrame(records).to_csv(output_dir / "news_retry_results.csv", index=False)
    counts = pd.Series([record["status"] for record in records], dtype="string").value_counts().to_dict()
    return {
        "audited_states": len(audit_rows),
        "unavailable_sources": len(targets),
        "retried_sources": len(records),
        "new_retries_this_run": len(pending),
        "retry_status_counts": counts,
        "coverage_audit": str(output_dir / "news_coverage_audit.csv"),
        "retry_results": str(output_dir / "news_retry_results.csv"),
        "note": "Supplemental source retries do not overwrite first-pass model decisions.",
    }


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
    return pd.DataFrame([
        {**{key: entry.get(key) for key in columns}, "raw_return": entry.get("raw")}
        for entry in entries
    ], columns=columns)


def run(
    data_dir: Path,
    output_dir: Path,
    run_id: str,
    pilot: bool,
    parallel_tickers: bool = False,
    risk_management_enabled: bool = True,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_store = output_dir / "run_files"
    yfinance_cache_dir = run_store / "yfinance_cache"
    yfinance_cache_dir.mkdir(parents=True, exist_ok=True)

    # Keep yfinance's SQLite cookie cache inside the run directory for restricted user profiles.
    import yfinance as yf
    yf.set_tz_cache_location(str(yfinance_cache_dir))

    from tradingagents.backtest import run_backtest
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.memory import TradingMemoryLog

    dates = load_sessions(data_dir)
    selected_dates = dates[-1:] if pilot else dates
    expected = {(ticker, date) for ticker in TICKERS for date in selected_dates}
    config = DEFAULT_CONFIG.copy()
    config["results_dir"] = str(run_store / "results")
    config["data_cache_dir"] = str(run_store / "cache")
    config["memory_log_path"] = str(run_store / "memory" / "unused.md")
    config["risk_management_enabled"] = risk_management_enabled

    logging.getLogger("tradingagents.backtest").setLevel(logging.ERROR)

    def progress(done: int, total: int, ticker: str, date: str) -> None:
        print(f"[{done}/{total}] {ticker} {date}", flush=True)

    if parallel_tickers:
        result = _run_parallel_backtest(
            list(TICKERS), selected_dates, config,
            selected_analysts=ANALYSTS, run_id=run_id, progress=progress,
        )
    else:
        result = run_backtest(
            list(TICKERS), selected_dates, config,
            selected_analysts=ANALYSTS, run_id=run_id, progress=progress,
        )
    entries = TradingMemoryLog({"memory_log_path": str(result.log_path)}).load_entries()
    stored = {(entry["ticker"], entry["date"]) for entry in entries}
    missing = sorted(expected - stored)
    rows = _entry_rows(entries).sort_values(["date", "ticker"])
    rows.to_csv(output_dir / "decision_cells.csv", index=False)

    news_retry = None
    if not pilot:
        news_retry = _audit_and_retry_news(
            output_dir, run_store, run_id, list(TICKERS), selected_dates, config,
        )

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
        "news_retry": news_retry,
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
    parser.add_argument("--parallel-tickers", action="store_true", help="Run each ticker concurrently, preserving date order")
    parser.add_argument(
        "--ablate-risk-management", action="store_true",
        help="Ablate the risk debate team and pass the Trader proposal to the Portfolio Manager",
    )
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    status = run(
        args.data_dir, output_dir, args.run_id, args.pilot,
        args.parallel_tickers, not args.ablate_risk_management,
    )
    if status["missing_cells"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
