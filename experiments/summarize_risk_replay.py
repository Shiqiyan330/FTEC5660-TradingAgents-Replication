"""Validate paired cells and report variability across independent trial means."""

import argparse
import csv
import json
from pathlib import Path
import statistics

from experiments.run_risk_replay import TICKERS, digest, frozen_prefix


def summarize(records, inputs, trials=3):
    expected = {(trial, ticker, condition) for trial in range(1, trials + 1)
                for ticker in TICKERS for condition in ("full", "no_risk")}
    indexed = {(r["trial"], r["ticker"], r["condition"]): r for r in records}
    if len(indexed) != len(records) or set(indexed) != expected:
        raise ValueError("missing, duplicate or unexpected replay cells")
    settings = records[0]["settings"]
    rows = []
    # Hold/REVIEW retain the starting weight, explicitly zero in this one-date slice.
    targets = {"Buy": 100, "Overweight": 75, "Underweight": 50,
               "Sell": 0, "Hold": 0, "REVIEW": 0}
    for trial, ticker, condition in sorted(expected):
        record = indexed[trial, ticker, condition]
        enabled = condition == "full"
        source = inputs[ticker]
        if (record["settings"] != settings or record["risk_management_enabled"] != enabled
                or record["input_sha256"] != digest(frozen_prefix(source["state"]))
                or record["source_state_sha256"] != source["source_state_sha256"]):
            raise ValueError("configuration or common-input mismatch")
        count = record["risk_debate_state"]["count"]
        if count != (3 * settings["max_risk_discuss_rounds"] if enabled else 0):
            raise ValueError("incorrect risk routing")
        rows.append({"trial": trial, "ticker": ticker, "condition": condition,
                     "rating": record["final_rating"],
                     "target_weight_pct": targets[record["final_rating"]],
                     "risk_turns": count, "input_sha256": record["input_sha256"]})
    trial_rows = []
    for trial in range(1, trials + 1):
        means = {condition: statistics.mean(
            r["target_weight_pct"] for r in rows
            if r["trial"] == trial and r["condition"] == condition
        ) for condition in ("full", "no_risk")}
        changed = sum(indexed[trial, t, "full"]["final_rating"] !=
                      indexed[trial, t, "no_risk"]["final_rating"] for t in TICKERS)
        trial_rows.append({"trial": trial, **means,
                           "delta_pp": means["no_risk"] - means["full"],
                           "changed_ratings": changed})
    stats = {}
    for column in ("full", "no_risk", "delta_pp"):
        values = [r[column] for r in trial_rows]
        stats[column] = {"mean": statistics.mean(values),
                         "sample_variance_pp2": statistics.variance(values),
                         "sample_sd_pp": statistics.stdev(values)}
    return {"trials": trials, "tickers": list(TICKERS), "cells": len(rows),
            "input_date": "2024-03-28", "settings": settings,
            "initial_weight_pct": 0, "trial_means": trial_rows, "statistics": stats,
            "interpretation": "variability across trial means; not 9 independent market dates",
            "rating_rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("experiments/results/risk_replay"))
    args = parser.parse_args()
    inputs = {t: json.loads((args.root / "inputs" / f"{t}.json").read_text(encoding="utf-8")) for t in TICKERS}
    records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((args.root / "cells").glob("trial*.json"))]
    summary = summarize(records, inputs)
    (args.root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for name, rows in (("ratings", summary["rating_rows"]), ("trial_means", summary["trial_means"])):
        with (args.root / f"{name}.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({k: v for k, v in summary.items() if k != "rating_rows"}, indent=2))


if __name__ == "__main__":
    main()
