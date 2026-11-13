# TradingAgents Reproduction Status

## Paper experiment target

The paper describes a simulation from 2024-01-01 through 2024-03-29 and names AAPL, NVDA, MSFT, META, and Google in the setup. Table 1 reports only AAPL, GOOGL, and AMZN, so its reported table and its described universe do not fully agree. Table 1 compares TradingAgents with Buy and Hold, MACD, KDJ+RSI, ZMR, and SMA, using cumulative return (CR), annualized return (AR), Sharpe ratio (SR), and maximum drawdown (MDD).

Paper: https://arxiv.org/html/2412.20138

## Experiment configuration

- Inputs: Yahoo daily OHLCV and adjusted close for AAPL, GOOGL, and AMZN, plus the Federal Reserve DGS3MO daily 3-month Treasury yield. Price history includes indicator warm-up dates from 2023-01-03; the evaluation window has 61 sessions from 2024-01-02 through 2024-03-28.
- Capital and execution: $100,000 per ticker, long-only target exposure, signal calculated after close and filled at the next session open. Adjusted OHLC is raw OHLC multiplied by `Adj Close / Close`; portfolio valuation uses adjusted close.
- Trading costs: commission 0 bps per order (commission-free); slippage 5 bps per order. No cost sensitivity test is run.
- TradingAgents rating weights: Buy 100%, Overweight 75%, Hold retains the prior target, Underweight 50%, Sell 0%; REVIEW retains the prior target.
- Baselines: MACD EMA(12,26,9), long when MACD exceeds its signal; KDJ(9,3,3) plus RSI(14), enter on K crossing above D with K<30 and RSI<50, exit on K crossing below D with K>80 or RSI>70; ZMR uses the 20-session close z-score, entering at z<=-2 and exiting at z>=0; SMA is long when SMA(20)>SMA(50); Buy-and-Hold targets 100% from the first session open.
- Metrics: CR is final equity over initial capital minus one. AR uses the paper's geometric formula over the 88 calendar days between the stated start and end dates. Sharpe is mean daily excess return over the prior available DGS3MO observation divided by the sample standard deviation of daily portfolio returns, annualized by `sqrt(252)`. MDD is the positive peak-to-trough percentage.

The detailed commands and rule definitions are in [experiments/README.md](experiments/README.md). Included input snapshots are in `experiments/data/table1`; recalculated metrics, equity curves and scoring configuration are in `experiments/results/table1_baselines`.

## Baseline results

Returns and drawdown are percentages. Paper values are Table 1 CR; local AR, Sharpe, MDD, and order counts use the configuration above.

| Ticker | Strategy | Local CR | Local AR | Local Sharpe | Local MDD | Orders | Paper CR |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AAPL | Buy & Hold | -8.30 | -30.21 | -1.97 | 13.30 | 1 | -5.23 |
| AAPL | MACD | -6.03 | -22.76 | -2.47 | 8.33 | 3 | -1.49 |
| AAPL | KDJ + RSI | -6.69 | -24.98 | -1.69 | 13.30 | 1 | 2.05 |
| AAPL | ZMR | 5.55 | 25.12 | 1.62 | 1.89 | 4 | 0.57 |
| AAPL | SMA | 0.91 | 3.85 | -0.17 | 1.89 | 2 | -3.20 |
| GOOGL | Buy & Hold | 8.88 | 42.35 | 1.21 | 14.40 | 1 | 7.78 |
| GOOGL | MACD | 5.23 | 23.56 | 0.84 | 8.74 | 5 | 6.20 |
| GOOGL | KDJ + RSI | 12.40 | 62.46 | 3.46 | 1.34 | 1 | 0.40 |
| GOOGL | ZMR | 2.75 | 11.90 | 0.67 | 5.10 | 2 | -0.58 |
| GOOGL | SMA | -1.26 | -5.12 | -0.32 | 11.67 | 2 | 6.23 |
| AMZN | Buy & Hold | 18.97 | 105.65 | 2.63 | 4.65 | 1 | 17.10 |
| AMZN | MACD | 4.94 | 22.13 | 0.79 | 5.74 | 6 | N/A |
| AMZN | KDJ + RSI | 0.00 | 0.00 | N/A | 0.00 | 0 | -0.77 |
| AMZN | ZMR | 0.00 | 0.00 | N/A | 0.00 | 0 | -0.77 |
| AMZN | SMA | 20.84 | 119.37 | 2.89 | 4.22 | 1 | 11.01 |

## Agent reproduction and fixed-model risk ablation

The graph runs locally in Conda `fin-agent-sakura`. Both quick and deep model identifiers are `gpt-6-luna` through the configured OpenAI-compatible gateway. This differs from the paper's backbone and does not establish exact historical Table 1 agent performance.

End-to-end diagnostics exposed a dead inherited proxy and a non-writable yfinance SQLite cache. The experiment runner now stores yfinance's cookie/time-zone databases in its own writable output folder. Process-local removal of the dead proxy restored inference. Native pending-entry settlement succeeded without resampling existing decisions. Historical news/social sources still have missing data and occasional SEC/FRED SSL failures; see the report and diagnostic inventory.

The controlled modification disables only the three-perspective risk discussion, retaining the Portfolio Manager and its explicit no-debate prompt. The experiment freezes the same analysts/research/Trader state for both conditions. It reuses the project's original risk and manager factories and router. All 18 cells (3 tickers x 2 conditions x 3 stochastic trials) completed and passed shared-input hashes, model and risk-turn invariants.

Across trial means, full target weights are 16.67%, 16.67%, 33.33%; no-risk weights are 50%, 50%, 50%. No-risk minus full averages +27.78 percentage points (sample variance 92.59 pp squared; SD 9.62 pp). Five of nine paired decisions differ. These are behavioral metrics under the local rating mapping, not portfolio returns or drawdown results. The 61-session agent portfolio and the paper's exact performance remain unmeasured.

Artifacts: [manifest and common inputs](experiments/results/risk_replay), [offline summarizer](experiments/summarize_risk_replay.py), [report](reports/reproducibility_report.pdf), [upstream code-change audit](reports/upstream_change_audit.md), [submission audit](reports/submission_audit.md).

## Submission blockers

The report and experiment artifacts are published in commit `8e6a2ad` to the private replication branch `qiyan/luna-sentiment-adapter`. The instructor needs repository access, and the student must provide the <=15-minute recorded presentation link. See [the human checklist](reports/HUMAN_IN_LOOP.md).
