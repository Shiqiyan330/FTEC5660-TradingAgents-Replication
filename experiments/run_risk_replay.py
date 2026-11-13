"""Paired risk-team ablation on frozen post-Trader states; no live data tools."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

from langgraph.graph import END, START, StateGraph

from tradingagents.agents import (
    AgentState, create_aggressive_debator, create_conservative_debator,
    create_neutral_debator, create_portfolio_manager,
)
from tradingagents.dataflows.config import run_config
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.graph.propagation import Propagator
from tradingagents.graph.setup import RISK_ANALYSIS_PATH_MAP
from tradingagents.llm_clients.factory import build_llm_kwargs, create_tier_client, tier_provider


TICKERS = ("AAPL", "GOOGL", "AMZN")
PREFIX_KEYS = (
    "market_report", "sentiment_report", "news_report", "fundamentals_report",
    "investment_debate_state", "investment_plan", "trader_investment_plan",
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def frozen_prefix(saved):
    """Exclude the previous risk debate, final decision and future reflections."""
    state = Propagator().create_initial_state(saved["company_of_interest"], saved["trade_date"])
    for key in PREFIX_KEYS:
        if not saved.get(key):
            raise ValueError(f"missing upstream field: {key}")
        state[key] = deepcopy(saved[key])
    return state


def workflow(quick, deep, enabled, rounds=1):
    graph = StateGraph(AgentState)
    graph.add_node("Portfolio Manager", create_portfolio_manager(deep, enabled))
    if enabled:
        graph.add_node("Aggressive Analyst", create_aggressive_debator(quick))
        graph.add_node("Conservative Analyst", create_conservative_debator(quick))
        graph.add_node("Neutral Analyst", create_neutral_debator(quick))
        graph.add_edge(START, "Aggressive Analyst")
        logic = ConditionalLogic(max_risk_discuss_rounds=rounds)
        for node in ("Aggressive Analyst", "Conservative Analyst", "Neutral Analyst"):
            graph.add_conditional_edges(node, logic.should_continue_risk_analysis, RISK_ANALYSIS_PATH_MAP)
    else:
        graph.add_edge(START, "Portfolio Manager")
    graph.add_edge("Portfolio Manager", END)
    return graph.compile()


def run(inputs, output, trials):
    config = deepcopy(DEFAULT_CONFIG)
    settings = {
        **{f"{tier}_think_llm": config[f"{tier}_think_llm"] for tier in ("quick", "deep")},
        **{f"{tier}_think_provider": tier_provider(config, tier) for tier in ("quick", "deep")},
        "llm_kwargs": build_llm_kwargs(config),
        "max_risk_discuss_rounds": config["max_risk_discuss_rounds"],
        "output_language": config.get("output_language", "English"),
    }
    prefixes = {}
    for ticker in TICKERS:
        saved = json.loads((inputs / f"{ticker}.json").read_text(encoding="utf-8"))
        for key in ("quick_think_llm", "deep_think_llm"):
            if settings[key] != saved["source_run_settings"][key]:
                raise ValueError(f"model differs from frozen source: {key}")
        prefixes[ticker] = saved
    output.mkdir(parents=True, exist_ok=True)
    quick = create_tier_client(config, "quick").get_llm()
    deep = create_tier_client(config, "deep").get_llm()

    def cell(ticker, trial, enabled):
        name = "full" if enabled else "no_risk"
        path = output / f"trial{trial}_{ticker}_{name}.json"
        saved = prefixes[ticker]
        initial = frozen_prefix(saved["state"])
        identity = {
            "trial": trial, "ticker": ticker, "condition": name,
            "risk_management_enabled": enabled, "settings": settings,
            "input_sha256": digest(initial),
            "source_state_sha256": saved["source_state_sha256"],
        }
        if path.exists():
            prior = json.loads(path.read_text(encoding="utf-8"))
            if any(prior[key] != value for key, value in identity.items()):
                raise ValueError(f"incompatible resume: {path}")
            print(f"skipped trial {trial} {ticker} {name}", flush=True)
            return
        print(f"started trial {trial} {ticker} {name}", flush=True)
        started = time.monotonic()
        with run_config({**config, "risk_management_enabled": enabled}):
            result = workflow(quick, deep, enabled, settings["max_risk_discuss_rounds"]).invoke(initial)
        expected_count = 3 * settings["max_risk_discuss_rounds"] if enabled else 0
        if result["risk_debate_state"]["count"] != expected_count:
            raise ValueError("unexpected risk debate turn count")
        record = {
            **identity, "elapsed_seconds": time.monotonic() - started,
            "final_rating": result["final_rating"],
            "final_trade_decision": result["final_trade_decision"],
            "risk_debate_state": result["risk_debate_state"],
        }
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        print(f"finished trial {trial} {ticker} {name}: {record['final_rating']}", flush=True)

    # The two conditions share exactly the same prefix. Alternate which runs first.
    def pair(ticker, trial):
        for enabled in ((True, False) if trial % 2 else (False, True)):
            cell(ticker, trial, enabled)

    for trial in range(1, trials + 1):
        with ThreadPoolExecutor(max_workers=3) as executor:
            list(executor.map(lambda ticker: pair(ticker, trial), TICKERS))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=Path("experiments/results/risk_replay/inputs"))
    parser.add_argument("--output", type=Path, default=Path("experiments/results/risk_replay/cells"))
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()
    if args.trials < 3:
        parser.error("at least three stochastic trials are required")
    run(args.inputs, args.output, args.trials)


if __name__ == "__main__":
    main()
