# TradingAgents Reproduction Status

## Paper experiment target

The paper describes a simulation from 2024-01-01 through 2024-03-29 and names AAPL, NVDA, MSFT, META, and Google in the setup. Table 1 reports only AAPL, GOOGL, and AMZN, so its reported table and its described universe do not fully agree. Table 1 compares TradingAgents with Buy and Hold, MACD, KDJ+RSI, ZMR, and SMA, using cumulative return (CR), annualized return (AR), Sharpe ratio (SR), and maximum drawdown (MDD).

Paper: https://arxiv.org/html/2412.20138

## What the current checkout supports

- The local TradingAgents smoke run completed one historical analysis: AAPL on 2024-03-28, rated Underweight, with GPT-6 Luna configured for both model tiers.
- `tradingagents/backtest.py` runs independent ticker/date decisions and scores their later five-trading-day return and benchmark-relative alpha. It does not carry positions or cash and does not produce an equity curve or CR/AR/SR/MDD.
- The official vectorbt source is cloned beside this checkout and installed as version 1.2.1 in its own `.venv`. A synthetic `Portfolio.from_signals` smoke test passed; the TradingAgents checkout and global Python were left unchanged.
- Yahoo OHLCV was fetched for all three Table 1 tickers, including indicator warm-up history: 311 rows each from 2023-01-03 through 2024-03-28. Each ticker has the same 61 sessions in the paper window, 2024-01-02 through 2024-03-28, with no missing OHLCV or adjusted-close fields.
- Buy-and-Hold was calculated from adjusted close with zero fees and a 0% risk-free rate. MDD is shown as a positive magnitude. This is a pipeline check, not a reproduction result:

| Ticker | Local CR | Local AR | Local SR | Local MDD | Paper CR | Paper AR | Paper SR | Paper MDD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AAPL | -7.51% | -37.32% | -1.84 | 13.30% | -5.23% | -5.09% | -1.29 | 11.90% |
| GOOGL | 9.24% | 69.65% | 1.74 | 14.40% | 7.78% | 8.09% | 1.35 | 13.04% |
| AMZN | 20.31% | 202.33% | 3.63 | 4.22% | 17.10% | 17.60% | 3.53 | 3.80% |

- Price-field check: AAPL's unadjusted Close gives CR -7.63% versus -7.51% from Adj Close, only 0.12 percentage points apart. GOOGL and AMZN have identical Close- and Adj-Close-based CRs for this window. Dividend adjustment therefore does not explain the 1.4-3.2 percentage-point CR gaps against Table 1.

## Reproduction gaps to resolve

1. The paper does not publish exact signal parameters for MACD, KDJ+RSI, ZMR, or SMA. The repository's earliest `v0.1.0` history has the paper results page and generic strategy descriptions, but no reusable baseline implementation. Choosing conventional defaults would make a documented approximation, not an exact reproduction.
2. The paper describes Buy/Sell/Hold signals and shows long/short markers, but it does not define position sizing, how Hold carries a position, or the execution price in enough detail to reconstruct its portfolio ledger.
3. The paper's stated annualized-return formula is inconsistent with its reported table over a roughly three-month period. Applying the formula to the reported AAPL CR of -5.23% yields about -19.82% annualized, not the table's -5.09%; applying it to TradingAgents CR of 26.62% yields about 163.95%, not 30.50%. Conversely, the CR/AR pairs imply about 352-375 days for Buy-and-Hold and 324-343 days for TradingAgents, rather than the stated 89-day window. This suggests the table may use a different run window or inconsistent annualization. Its Sharpe formula also does not state an annualization convention.
4. The current repository is a later version than the paper experiment, uses a configurable provider, and the completed smoke run used GPT-6 Luna. Model, data vendor, and agent version therefore differ from the paper setup.
5. The paper notes that one prediction required about 11 LLM calls and 20+ tool calls. Applying that to 61 sessions and the three Table 1 tickers is around 2,013 LLM calls, before retries; a full daily rerun needs an explicit cost/scope decision.

## Next steps

1. Record parameter assumptions for the four technical baselines and settle the annualization/risk-free-rate conventions; run the baselines offline first against the now-validated prices.
2. Choose a TradingAgents position and execution rule, then run a bounded model pilot before deciding whether to expand to every session. VectorBT's docs advise shifting close-derived signals one bar forward before execution: https://vectorbt.dev/api/portfolio/base/.
3. Export one row per ticker/date/rating and one daily portfolio value series; calculate CR, AR, SR, and MDD under the same stated conventions for all strategies.

Until the trading rules, baseline parameters, and model-run scope are recorded, any Table 1 comparison must be labelled an approximation.
