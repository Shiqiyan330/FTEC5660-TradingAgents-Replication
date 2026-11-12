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
- Metrics: CR is final equity over initial capital minus one. AR uses the paper's geometric formula over the 88 calendar days between the stated start and end dates. Sharpe uses daily excess return over the prior available DGS3MO observation and annualizes by `sqrt(252)`. MDD is the positive peak-to-trough percentage.

The detailed command, rule definitions, and generated output schema are in [experiments/README.md](experiments/README.md). The run configuration and CSV outputs are under the local `smoke_test/table1_results_final/` directory.

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

## Remaining work

- Planned fixed-model ablation: disable the three-agent Risk Management Team while retaining the analyst team, researcher debate, Trader, memory, data, dates, and scoring. The ablated path sends the Trader proposal directly to the Portfolio Manager, with a prompt that explicitly states no risk debate occurred. The original paper argues that risk-management debate supports drawdown control but reports no component-level ablation; this experiment measures that claim in the reproduction setup. The runner exposes `--ablate-risk-management`; run the full and ablated conditions in separate output directories and with identical model/provider settings before reporting an effect.
- Ablation results are pending. A full run makes many hosted-model calls and must not be represented by the existing single-day smoke test or the baseline-only results below.
- The paper does not disclose the technical-indicator parameters, execution price, position sizing, commission, or slippage used for Table 1. The parameters above make each local result reproducible.
- The paper's setup names AAPL, NVDA, MSFT, META, and Google, while Table 1 reports AAPL, GOOGL, and AMZN.
- Applying the paper's stated annualized-return formula to its AAPL Buy-and-Hold CR (-5.23%) over the 88-day evaluation window gives about -19.82%, while Table 1 reports -5.09%. The table's CR/AR values therefore do not follow that formula over the stated window. The paper also does not define Sharpe annualization.
- The existing smoke analysis is AAPL on 2024-03-28, rated Underweight, using GPT-6 Luna for both model tiers. The expanded three-ticker pilot for 2024-03-28 was attempted with matching settings, but all three cells failed with a model `Connection error`; zero new decisions were stored. A read-only `/models` connectivity check returned `ProxyError`. The resumable runner and rating-to-portfolio scorer are in `experiments/`; the 183-cell full run and TradingAgents Table 1 rows remain pending a working model connection.
