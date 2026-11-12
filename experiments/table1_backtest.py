"""Run the TradingAgents paper's Table 1 baselines on the stated paper window."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt

TICKERS = ("AAPL", "GOOGL", "AMZN")
PAPER_START = pd.Timestamp("2024-01-01")
PAPER_END = pd.Timestamp("2024-03-29")
INITIAL_CASH = 100_000.0
COMMISSION_BPS = 0.0
SLIPPAGE_BPS = 5.0
TRADING_DAYS_PER_YEAR = 252
PERIOD_YEARS = (PAPER_END - PAPER_START).days / 365.25

PAPER_RESULTS = {
    "AAPL": {
        "Buy & Hold": (-5.23, -5.09, -1.29, 11.90),
        "MACD": (-1.49, -1.48, -0.81, 4.53),
        "KDJ + RSI": (2.05, 2.07, 1.64, 1.09),
        "ZMR": (0.57, 0.57, 0.17, 0.86),
        "SMA": (-3.20, -2.97, -1.72, 3.67),
    },
    "GOOGL": {
        "Buy & Hold": (7.78, 8.09, 1.35, 13.04),
        "MACD": (6.20, 6.26, 2.31, 1.22),
        "KDJ + RSI": (0.40, 0.40, 0.02, 1.58),
        "ZMR": (-0.58, 0.58, 2.12, 2.34),
        "SMA": (6.23, 6.43, 2.12, 2.34),
    },
    "AMZN": {
        "Buy & Hold": (17.10, 17.60, 3.53, 3.80),
        "MACD": None,
        "KDJ + RSI": (-0.77, -0.76, -2.25, 1.08),
        "ZMR": (-0.77, -0.77, -2.45, 0.82),
        "SMA": (11.01, 11.60, 2.22, 3.97),
    },
}


def load_prices(data_dir: Path, ticker: str) -> pd.DataFrame:
    """Load Yahoo OHLCV and convert OHLC to the adjusted-close price basis."""
    frame = pd.read_csv(data_dir / f"{ticker}.csv", parse_dates=["Date"])
    required = ("Date", "Open", "High", "Low", "Close", "Adj Close")
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"{ticker} is missing columns: {sorted(missing)}")
    frame = frame.set_index("Date").sort_index()
    if frame.index.has_duplicates:
        raise ValueError(f"{ticker} has duplicate dates")
    values = frame[["Open", "High", "Low", "Close", "Adj Close"]].apply(pd.to_numeric, errors="coerce")
    if values.isna().any().any() or (values["Close"] <= 0).any():
        raise ValueError(f"{ticker} has missing or invalid prices")
    adjustment = values["Adj Close"] / values["Close"]
    return pd.DataFrame({
        "Open": values["Open"] * adjustment,
        "High": values["High"] * adjustment,
        "Low": values["Low"] * adjustment,
        "Close": values["Adj Close"],
    }, index=frame.index)


def load_daily_risk_free(data_dir: Path, price_dates: pd.DatetimeIndex) -> pd.Series:
    """Use the prior available DGS3MO observation, converted to a daily return."""
    frame = pd.read_csv(data_dir / "DGS3MO.csv", na_values=["."])
    if not {"observation_date", "DGS3MO"}.issubset(frame.columns):
        raise ValueError("DGS3MO.csv must contain observation_date and DGS3MO")
    annual_yield = pd.Series(
        pd.to_numeric(frame["DGS3MO"], errors="coerce").to_numpy(),
        index=pd.to_datetime(frame["observation_date"]),
    ).dropna().sort_index()
    aligned = annual_yield.reindex(price_dates).ffill().shift(1)
    daily = (1 + aligned / 100) ** (1 / TRADING_DAYS_PER_YEAR) - 1
    return daily


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    change = close.diff()
    gains = change.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    losses = (-change.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    relative_strength = gains / losses
    return 100 - 100 / (1 + relative_strength)


def _kdj(high: pd.Series, low: pd.Series, close: pd.Series) -> tuple[pd.Series, pd.Series]:
    lowest = low.rolling(9, min_periods=9).min()
    highest = high.rolling(9, min_periods=9).max()
    span = highest - lowest
    rsv = (close - lowest) / span.replace(0, np.nan) * 100
    rsv = rsv.where(lowest.notna())
    rsv = rsv.mask(span.eq(0), 50.0)
    k = pd.Series(np.nan, index=close.index, dtype=float)
    d = pd.Series(np.nan, index=close.index, dtype=float)
    first = rsv.first_valid_index()
    if first is None:
        return k, d
    start = close.index.get_loc(first)
    previous_k = previous_d = 50.0
    for i in range(start, len(close)):
        previous_k = (2 * previous_k + rsv.iloc[i]) / 3
        previous_d = (2 * previous_d + previous_k) / 3
        k.iloc[i], d.iloc[i] = previous_k, previous_d
    return k, d


def _position_from_events(entries: pd.Series, exits: pd.Series) -> pd.Series:
    """Convert entry/exit events to a persistent long-or-flat position."""
    position = 0.0
    result = []
    for entry, exit_ in zip(entries.fillna(False), exits.fillna(False)):
        if exit_:
            position = 0.0
        elif entry:
            position = 1.0
        result.append(position)
    return pd.Series(result, index=entries.index, dtype=float)


def targets_after_close(prices: pd.DataFrame) -> dict[str, pd.Series]:
    close = prices["Close"]

    macd_line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_target = (macd_line > macd_signal).astype(float)

    k, d = _kdj(prices["High"], prices["Low"], close)
    rsi = _rsi(close)
    k_cross_up = (k > d) & (k.shift(1) <= d.shift(1))
    k_cross_down = (k < d) & (k.shift(1) >= d.shift(1))
    kdj_entries = k_cross_up & (k < 30) & (rsi < 50)
    kdj_exits = (k_cross_down & (k > 80)) | (rsi > 70)

    rolling_mean = close.rolling(20, min_periods=20).mean()
    rolling_std = close.rolling(20, min_periods=20).std(ddof=0)
    z_score = (close - rolling_mean) / rolling_std.replace(0, np.nan)
    zmr_entries = z_score <= -2
    zmr_exits = z_score >= 0

    sma_short = close.rolling(20, min_periods=20).mean()
    sma_long = close.rolling(50, min_periods=50).mean()
    sma_target = (sma_short > sma_long).astype(float)

    return {
        "Buy & Hold": pd.Series(1.0, index=prices.index),
        "MACD": macd_target.fillna(0.0),
        "KDJ + RSI": _position_from_events(kdj_entries, kdj_exits),
        "ZMR": _position_from_events(zmr_entries, zmr_exits),
        "SMA": sma_target.fillna(0.0),
    }


def target_for_rating(rating: str, current_weight: float) -> float:
    """Map the five TradingAgents ratings to a long-only target exposure."""
    targets = {"Buy": 1.0, "Overweight": 0.75, "Underweight": 0.50, "Sell": 0.0}
    return current_weight if rating in {"Hold", "REVIEW"} else targets[rating]


def targets_for_execution(
    target_after_close: pd.Series,
    evaluation_dates: pd.DatetimeIndex,
    *,
    buy_and_hold: bool = False,
) -> pd.Series:
    """Shift close-derived decisions to the next open; begin flat at period start."""
    if buy_and_hold:
        return pd.Series(1.0, index=evaluation_dates, dtype=float)
    target = target_after_close.shift(1).reindex(evaluation_dates).fillna(0.0).astype(float)
    if len(target):
        target.iloc[0] = 0.0
    return target


def _orders_for_targets(targets: pd.Series) -> pd.Series:
    previous = targets.shift(1, fill_value=0.0)
    return targets.where(targets.ne(previous), np.nan)


def simulate(
    close: pd.Series,
    open_: pd.Series,
    target_weights: pd.Series,
    *,
    commission_bps: float = COMMISSION_BPS,
    slippage_bps: float = SLIPPAGE_BPS,
) -> vbt.Portfolio:
    if not 0 <= commission_bps < 10_000 or not 0 <= slippage_bps < 10_000:
        raise ValueError("commission and slippage must be between 0 and 10,000 basis points")
    return vbt.Portfolio.from_orders(
        close,
        size=_orders_for_targets(target_weights),
        size_type="targetpercent",
        price=open_,
        val_price=open_,
        fees=commission_bps / 10_000,
        slippage=slippage_bps / 10_000,
        init_cash=INITIAL_CASH,
        freq="1D",
    )


def score_portfolio(
    portfolio: vbt.Portfolio,
    daily_risk_free: pd.Series,
) -> dict[str, float | int]:
    nav = portfolio.value()
    prior_nav = nav.shift(1, fill_value=INITIAL_CASH)
    returns = nav / prior_nav - 1
    risk_free = daily_risk_free.reindex(nav.index)
    excess = returns - risk_free
    volatility = returns.std(ddof=1)
    sharpe = (np.sqrt(TRADING_DAYS_PER_YEAR) * excess.mean() / volatility
              if volatility and np.isfinite(volatility) else np.nan)

    extended_nav = pd.concat([
        pd.Series([INITIAL_CASH], index=[nav.index[0] - pd.Timedelta(days=1)]),
        nav,
    ])
    drawdown = extended_nav / extended_nav.cummax() - 1
    final_value = float(nav.iloc[-1])
    return {
        "cr_pct": (final_value / INITIAL_CASH - 1) * 100,
        "ar_pct": ((final_value / INITIAL_CASH) ** (1 / PERIOD_YEARS) - 1) * 100,
        "sharpe": float(sharpe),
        "mdd_pct": max(0.0, float(-drawdown.min() * 100)),
        "final_value": final_value,
        "orders": int(portfolio.orders.count()),
    }


def run(data_dir: Path, output_dir: Path) -> pd.DataFrame:
    prices_by_ticker = {ticker: load_prices(data_dir, ticker) for ticker in TICKERS}
    dates = prices_by_ticker[TICKERS[0]].index
    if any(not frame.index.equals(dates) for frame in prices_by_ticker.values()):
        raise ValueError("Table 1 ticker date indexes do not match")
    evaluation_dates = dates[(dates >= PAPER_START) & (dates <= PAPER_END)]
    if len(evaluation_dates) != 61:
        raise ValueError(f"expected 61 paper-window sessions; found {len(evaluation_dates)}")

    daily_risk_free = load_daily_risk_free(data_dir, dates).reindex(evaluation_dates)
    if daily_risk_free.isna().any():
        raise ValueError("DGS3MO does not cover the paper window")

    rows = []
    base_equity = pd.DataFrame(index=evaluation_dates)
    for ticker, prices in prices_by_ticker.items():
        after_close = targets_after_close(prices)
        for strategy, target in after_close.items():
            weights = targets_for_execution(
                target,
                evaluation_dates,
                buy_and_hold=(strategy == "Buy & Hold"),
            )
            portfolio = simulate(
                prices.loc[evaluation_dates, "Close"],
                prices.loc[evaluation_dates, "Open"],
                weights,
                slippage_bps=SLIPPAGE_BPS,
            )
            metrics = score_portfolio(portfolio, daily_risk_free)
            paper = PAPER_RESULTS[ticker][strategy]
            rows.append({
                "ticker": ticker,
                "strategy": strategy,
                "commission_bps_per_order": COMMISSION_BPS,
                "slippage_bps_per_order": SLIPPAGE_BPS,
                **metrics,
                "paper_cr_pct": paper[0] if paper else np.nan,
                "paper_ar_pct": paper[1] if paper else np.nan,
                "paper_sharpe": paper[2] if paper else np.nan,
                "paper_mdd_pct": paper[3] if paper else np.nan,
            })
            base_equity[f"{ticker}_{strategy}"] = portfolio.value()

    output_dir.mkdir(parents=True, exist_ok=False)
    summary = pd.DataFrame(rows)
    summary.to_csv(output_dir / "table1_metrics.csv", index=False, float_format="%.6f")
    base_equity.index.name = "Date"
    base_equity.to_csv(output_dir / "table1_equity_curves.csv", float_format="%.6f")
    config = {
        "paper_window": [str(PAPER_START.date()), str(PAPER_END.date())],
        "price_basis": "Yahoo adjusted OHLC: raw OHLC multiplied by Adj Close / Close",
        "execution": "signals from date t close; target exposure filled at date t+1 open",
        "initial_cash_per_ticker": INITIAL_CASH,
        "rating_target_weights": {
            "Buy": 1.0, "Overweight": 0.75, "Hold": "retain prior target",
            "Underweight": 0.50, "Sell": 0.0, "REVIEW": "retain prior target",
        },
        "commission_bps_per_order": COMMISSION_BPS,
        "slippage_bps_per_order": SLIPPAGE_BPS,
        "risk_free_rate": "prior available DGS3MO observation converted from annual yield to daily rate",
        "sharpe_annualization": TRADING_DAYS_PER_YEAR,
        "annual_return_year_fraction": PERIOD_YEARS,
        "signal_parameters": {
            "MACD": "EMA(12)-EMA(26), signal EMA(9); long when MACD > signal",
            "KDJ + RSI": "KDJ(9,3,3), RSI(14); enter on K cross above D with K<30 and RSI<50; exit on K cross below D with K>80 or RSI>70",
            "ZMR": "20-session close z-score; enter at z<=-2; exit at z>=0",
            "SMA": "SMA(20)/SMA(50); long when SMA(20)>SMA(50)",
            "Buy & Hold": "100% target exposure from first session open",
        },
    }
    (output_dir / "run_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=root / "smoke_test" / "paper_prices")
    parser.add_argument("--output-dir", type=Path, default=root / "smoke_test" / "table1_results")
    args = parser.parse_args()
    summary = run(args.data_dir, args.output_dir)
    print(summary.to_string(index=False))
    print(f"\nSaved results to {args.output_dir}")


if __name__ == "__main__":
    main()
