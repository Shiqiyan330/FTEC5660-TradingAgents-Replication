"""Cache and audit Benzinga inputs for every Table 1 decision window."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from experiments.run_tradingagents_table1 import TICKERS, load_sessions
from tradingagents.agents.analysts.sentiment_analyst import _seven_days_back
from tradingagents.dataflows.config import run_config
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.vendors.benzinga.news import get_global_news, get_news


def audit(data_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    config = {**DEFAULT_CONFIG, "data_cache_dir": str(output_dir / "run_files" / "cache")}
    dates = load_sessions(data_dir)

    def fetch_source(symbol: str) -> list[dict]:
        records = []
        with run_config(config):
            for date in dates:
                try:
                    text = get_global_news(date) if symbol == "GLOBAL" else get_news(symbol, _seven_days_back(date), date)
                    count = sum(line.startswith("### ") for line in text.splitlines())
                    status = "articles" if count else "empty"
                    record = {"ticker": symbol, "date": date, "status": status, "articles": count}
                except Exception as exc:
                    record = {"ticker": symbol, "date": date, "status": "failed", "articles": 0, "error_type": type(exc).__name__}
                records.append(record)
                print(f"{symbol} {date}: {record['status']} ({record['articles']})", flush=True)
        return records

    rows = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for batch in executor.map(fetch_source, (*TICKERS, "GLOBAL")):
            rows.extend(batch)
    frame = pd.DataFrame(rows).sort_values(["date", "ticker"])
    frame.to_csv(output_dir / "benzinga_input_audit.csv", index=False)
    summary = {
        "provider": "benzinga",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "sessions": len(dates),
        "expected_windows": len(dates) * 4,
        "status_counts": frame["status"].value_counts().to_dict(),
        "company_windows_with_articles": int(((frame.ticker != "GLOBAL") & (frame.status == "articles")).sum()),
        "global_windows_with_articles": int(((frame.ticker == "GLOBAL") & (frame.status == "articles")).sum()),
        "input_audit": str(output_dir / "benzinga_input_audit.csv"),
    }
    (output_dir / "benzinga_input_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=root / "experiments" / "data" / "table1")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = audit(args.data_dir, args.output_dir)
    if summary["status_counts"].get("failed") or summary["status_counts"].get("empty"):
        raise SystemExit(2)

