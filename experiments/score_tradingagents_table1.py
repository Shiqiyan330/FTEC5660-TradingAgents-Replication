"""Map saved TradingAgents ratings to holdings and score the Table 1 portfolio."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from experiments.table1_backtest import (
    COMMISSION_BPS,
    INITIAL_CASH,
    PAPER_END,
    PAPER_RESULTS,
    PAPER_START,
    SLIPPAGE_BPS,
    TICKERS,
    load_daily_risk_free,
    load_prices,
    run as run_baselines,
    score_portfolio,
    simulate,
    target_for_rating,
    targets_for_execution,
)

PAPER_TRADINGAGENTS_RESULTS = {
    "AAPL": (26.62, 30.50, 8.21, 0.91),
    "GOOGL": (24.36, 27.58, 6.39, 1.69),
    "AMZN": (23.21, 24.90, 5.60, 2.11),
}


def build_targets(entries: pd.DataFrame, ticker: str, dates: pd.DatetimeIndex) -> tuple[pd.DataFrame, list[str]]:
    selected = entries.loc[entries["ticker"].eq(ticker)].copy()
    if selected["date"].duplicated().any():
        raise ValueError(f"duplicate model decisions for {ticker}")
    by_date = selected.set_index("date").to_dict("index")
    current_weight = 0.0
    rows, missing = [], []
    for date in dates:
        key = date.strftime("%Y-%m-%d")
        entry = by_date.get(key)
        rating = entry.get("rating") if entry else None
        if not rating:
            missing.append(key)
            rating = "REVIEW"
        current_weight = target_for_rating(rating, current_weight)
        rows.append({
            "date": key,
            "ticker": ticker,
            "rating": rating,
            "target_weight": current_weight,
            "decision": entry.get("decision", "") if entry else "",
        })
    return pd.DataFrame(rows), missing


def score(data_dir: Path, decision_file: Path, baseline_dir: Path, output_dir: Path) -> pd.DataFrame:
    decisions = pd.read_csv(decision_file, keep_default_na=False)
    indexes = {ticker: load_prices(data_dir, ticker).index for ticker in TICKERS}
    dates = indexes[TICKERS[0]]
    if any(not index.equals(dates) for index in indexes.values()):
        raise ValueError("Table 1 ticker date indexes do not match")
    dates = dates[(dates >= PAPER_START) & (dates <= PAPER_END)]
    target_frames, missing = [], {}
    for ticker in TICKERS:
        frame, absent = build_targets(decisions, ticker, dates)
        target_frames.append(frame)
        if absent:
            missing[ticker] = absent
    if missing:
        raise ValueError(f"incomplete TradingAgents decision grid: {missing}")

    if not (baseline_dir / "table1_metrics.csv").exists():
        run_baselines(data_dir, baseline_dir)
    baseline_metrics = pd.read_csv(baseline_dir / "table1_metrics.csv")
    equity = pd.read_csv(baseline_dir / "table1_equity_curves.csv", parse_dates=["Date"]).set_index("Date")
    risk_free = load_daily_risk_free(data_dir, indexes[TICKERS[0]]).reindex(dates)

    rows, orders = [], []
    for ticker, prices in ((ticker, load_prices(data_dir, ticker)) for ticker in TICKERS):
        target_frame = next(frame for frame in target_frames if frame["ticker"].iloc[0] == ticker)
        signal_weights = pd.Series(target_frame["target_weight"].to_numpy(), index=dates)
        execution_weights = targets_for_execution(signal_weights, dates)
        period = prices.loc[dates]
        portfolio = simulate(
            period["Close"], period["Open"], execution_weights,
            commission_bps=COMMISSION_BPS, slippage_bps=SLIPPAGE_BPS,
        )
        metrics = score_portfolio(portfolio, risk_free)
        paper = PAPER_TRADINGAGENTS_RESULTS[ticker]
        rows.append({
            "ticker": ticker,
            "strategy": "TradingAgents",
            "commission_bps_per_order": COMMISSION_BPS,
            "slippage_bps_per_order": SLIPPAGE_BPS,
            **metrics,
            "paper_cr_pct": paper[0],
            "paper_ar_pct": paper[1],
            "paper_sharpe": paper[2],
            "paper_mdd_pct": paper[3],
        })
        equity[f"{ticker}_TradingAgents"] = portfolio.value()
        order_frame = portfolio.orders.records_readable.copy()
        if not order_frame.empty:
            order_frame["ticker"] = ticker
            orders.append(order_frame)

    agent_metrics = pd.DataFrame(rows)
    combined = pd.concat([baseline_metrics, agent_metrics], ignore_index=True)
    improvement_rows = []
    for ticker in TICKERS:
        local_base = baseline_metrics.loc[baseline_metrics["ticker"].eq(ticker)]
        local_agent = agent_metrics.loc[agent_metrics["ticker"].eq(ticker)].iloc[0]
        improvement_rows.append({
            "ticker": ticker,
            "cr_improvement_ppt": local_agent["cr_pct"] - local_base["cr_pct"].max(),
            "ar_improvement_ppt": local_agent["ar_pct"] - local_base["ar_pct"].max(),
            "sharpe_improvement": local_agent["sharpe"] - local_base["sharpe"].max(),
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_dir / "table1_metrics.csv", index=False, float_format="%.6f")
    equity.index.name = "Date"
    equity.to_csv(output_dir / "table1_equity_curves.csv", float_format="%.6f")
    pd.concat(target_frames, ignore_index=True).to_csv(
        output_dir / "tradingagents_ratings_and_weights.csv", index=False,
    )
    pd.DataFrame(orders).to_csv(output_dir / "tradingagents_orders.csv", index=False)
    pd.DataFrame(improvement_rows).to_csv(
        output_dir / "table1_improvement.csv", index=False, float_format="%.6f",
    )
    config = {
        "paper_window": [str(PAPER_START.date()), str(PAPER_END.date())],
        "initial_cash_per_ticker": INITIAL_CASH,
        "rating_weights": {
            "Buy": 1.0, "Overweight": 0.75, "Hold": "retain prior target",
            "Underweight": 0.50, "Sell": 0.0, "REVIEW": "retain prior target",
        },
        "execution": "previous close decision filled at next session open; first session starts flat",
        "commission_bps_per_order": COMMISSION_BPS,
        "slippage_bps_per_order": SLIPPAGE_BPS,
        "sharpe_risk_free": "prior available DGS3MO observation, daily-converted annual yield",
        "sharpe_annualization": 252,
    }
    (output_dir / "scoring_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    _write_plots(equity, output_dir)
    return combined


def _write_plots(equity: pd.DataFrame, output_dir: Path) -> None:
    for ticker in TICKERS:
        fig = go.Figure()
        for column in equity.columns:
            if column.startswith(f"{ticker}_"):
                fig.add_trace(go.Scatter(
                    x=equity.index,
                    y=equity[column] / INITIAL_CASH * 100,
                    mode="lines",
                    name=column.removeprefix(f"{ticker}_"),
                ))
        fig.update_layout(
            title=f"{ticker}: Table 1 Strategy Comparison",
            xaxis_title="Date",
            yaxis_title="Portfolio value index (start = 100)",
            template="plotly_white",
            legend_title="Strategy",
        )
        fig.write_html(output_dir / f"{ticker}_equity_comparison.html", include_plotlyjs=True)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=root / "smoke_test" / "paper_prices")
    parser.add_argument("--decision-file", type=Path, default=root / "smoke_test" / "table1_agent_full" / "decision_cells.csv")
    parser.add_argument("--baseline-dir", type=Path, default=root / "smoke_test" / "table1_results_final")
    parser.add_argument("--output-dir", type=Path, default=root / "smoke_test" / "table1_agent_full" / "scored")
    args = parser.parse_args()
    summary = score(args.data_dir, args.decision_file, args.baseline_dir, args.output_dir)
    print(summary.loc[summary["strategy"].eq("TradingAgents")].to_string(index=False))
    print(f"\nSaved Table 1 results to {args.output_dir}")


if __name__ == "__main__":
    main()
