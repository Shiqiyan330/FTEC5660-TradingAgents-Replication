# TradingAgents Reproduction and Risk-Team Ablation

**Course:** FTEC5660 Agentic AI for Business and FinTech

**Author:** Qiyan Shi

**Repository:** <https://github.com/Shiqiyan330/FTEC5660-TradingAgents-Replication>

**Branch:** `qiyan/luna-sentiment-adapter`
**Scope:** Q1 2024 technical baselines plus a three-trial, frozen-input risk-team ablation dated 2024-03-28.

## 1. Project and reproduction target

TradingAgents combines specialist market, sentiment, news and fundamentals analysts; bull/bear researchers; a Research Manager; a Trader; aggressive, conservative and neutral risk analysts; and a Portfolio Manager. It is an agentic system because agents call tools, exchange intermediate reports, debate and produce a final trading decision over multiple steps. The source paper reports return and drawdown comparisons with technical strategies. [1]

This work has two measured targets. First, it reconstructs the five technical comparators in Table 1 for AAPL, GOOGL and AMZN over Q1 2024 under explicit execution rules. Second, it tests the claimed behavioral role of the risk-management stage on one clearly defined three-ticker subset. The assignment permits a small subset and behavior-level evaluation. The paper describes a broader stock universe than Table 1: the setup names AAPL, NVDA, MSFT, META and Google, whereas the table reports AAPL, GOOGL and AMZN. This work follows the table.

## 2. Setup and model control

Agent runs used local Windows Conda `fin-agent-sakura`, Python 3.11.15, TradingAgents 0.7.1, yfinance 1.3.0, LangGraph 1.2.0, langgraph-checkpoint-sqlite 3.1.3, langchain-openai 1.2.1 and OpenAI SDK 2.36.0. Both model tiers used the configured identifier `gpt-6-luna` through an OpenAI-compatible gateway at `https://sub.deuo.top/v1`. Both experimental conditions use the same gateway and model identifiers. The provider's underlying model identity is not independently established. Temperature, top-p, output cap and seed were not explicitly supplied; provider defaults and stochastic sampling apply. The machine-readable manifest records versions, endpoint host and settings without credentials.

The paper describes gpt-4o-mini/gpt-4o for quick tasks and o1-preview for deeper reasoning. [1] Our available model therefore differs from the paper, while remaining fixed between control and ablation. The results evaluate the current open-source implementation under this configuration. The local source starts from upstream commit `9fa1196`, with earlier screening adaptation and reproduction commits. Removing risk review is the one experimental modification; network/cache/export fixes support execution and measurement in both conditions.

Baseline scoring used the sibling vectorbt virtual environment (vectorbt 1.2.1, pandas 3.1.1, NumPy 2.5.4 and numba 0.68.1), because `fin-agent-sakura` lacks vectorbt. Agent-side pandas/NumPy are 3.0.3/2.4.4. API keys are read from the untracked local `.env`. No GPU is needed for hosted inference; this report makes no measured dollar-cost claim because provider billing/token telemetry was not captured.

## 3. Baseline method and metrics

Cached Yahoo daily OHLCV and adjusted-close inputs cover 2023-01-03 through 2024-03-28, providing indicator warm-up. Evaluation has 61 market sessions, 2024-01-02 through 2024-03-28, within the paper's stated 2024-01-01 to 2024-03-29 window. Adjusted OHLC is raw OHLC multiplied by `Adj Close / Close`. Inputs, SHA-256 checksums, metrics, equity curves and scoring configuration accompany the submission under `experiments/data/table1` and `experiments/results/table1_baselines`.

Local rules are MACD EMA(12,26,9); KDJ(9,3,3) with RSI(14), entering on a K/D upward cross with K<30 and RSI<50, exiting on a downward cross with K>80 or RSI>70; 20-session z-score mean reversion (entry <=-2, exit >=0); and SMA(20/50). Close-derived signals execute at the next session open. Strategies are long-only with $100,000 per ticker, zero commission and 5 bps order slippage. Buy & Hold starts invested at the first session open; signal strategies start flat. These choices are documented local assumptions, since the paper does not disclose the corresponding parameters, sizing, cost and execution details.

CR is final equity / initial capital minus one. AR uses the paper's geometric formula over the stated 88-calendar-day interval. Sharpe is mean daily excess return over the prior available DGS3MO daily risk-free rate, divided by the sample standard deviation of daily portfolio returns, annualized by sqrt(252). MDD is the positive peak-to-trough percentage. A zero-volatility portfolio has undefined Sharpe, reported as N/A. The paper does not specify Sharpe annualization.

## 4. Baseline results versus Table 1

The local numbers below were recalculated from the included snapshot. Paper CR values come from Table 1. The complete CSV also contains the paper's AR, Sharpe and MDD for comparison.

| Ticker | Strategy | Local CR % | Paper CR % | Local AR % | Local SR | Local MDD % |
|---|---|---:|---:|---:|---:|---:|
| AAPL | Buy & Hold | -8.30 | -5.23 | -30.21 | -1.97 | 13.30 |
| AAPL | MACD | -6.03 | -1.49 | -22.76 | -2.47 | 8.33 |
| AAPL | KDJ + RSI | -6.69 | 2.05 | -24.98 | -1.69 | 13.30 |
| AAPL | ZMR | 5.55 | 0.57 | 25.12 | 1.62 | 1.89 |
| AAPL | SMA | 0.91 | -3.20 | 3.85 | -0.17 | 1.89 |
| GOOGL | Buy & Hold | 8.88 | 7.78 | 42.35 | 1.21 | 14.40 |
| GOOGL | MACD | 5.23 | 6.20 | 23.56 | 0.84 | 8.74 |
| GOOGL | KDJ + RSI | 12.40 | 0.40 | 62.46 | 3.46 | 1.34 |
| GOOGL | ZMR | 2.75 | -0.58 | 11.90 | 0.67 | 5.10 |
| GOOGL | SMA | -1.26 | 6.23 | -5.12 | -0.32 | 11.67 |
| AMZN | Buy & Hold | 18.97 | 17.10 | 105.65 | 2.63 | 4.65 |
| AMZN | MACD | 4.94 | N/A | 22.13 | 0.79 | 5.74 |
| AMZN | KDJ + RSI | 0.00 | -0.77 | 0.00 | N/A | 0.00 |
| AMZN | ZMR | 0.00 | -0.77 | 0.00 | N/A | 0.00 |
| AMZN | SMA | 20.84 | 11.01 | 119.37 | 2.89 | 4.22 |

The reported values are not recovered exactly. For example, AAPL Buy & Hold is -8.30% locally versus -5.23% in the paper. Parameter and execution ambiguity prevents identifying a single cause. The paper's AAPL Buy & Hold CR of -5.23%, annualized over its 88-day window using its formula, gives approximately -19.82%, while its table gives AR -5.09%. Consequently the local result is a transparent reconstruction, not proof of the paper's exact trading implementation.

## 5. Why ablate the risk team?

The paper assigns risk agents the task of reviewing market exposure and risks from three viewpoints, and attributes risk control to their debate. [1] This makes the module a specific, testable target. A separate quantitative multi-agent paper's Table 3 reports maximum drawdown changing from -12.54% for its complete system to -16.27% without its Market Risk agent. [2] That different architecture motivates measuring risk review; it does not establish that this is TradingAgents' most important module or predict its effect size.

The treatment disables the aggressive/conservative/neutral discussion while retaining the Portfolio Manager. The no-risk prompt explicitly states that no debate took place and asks the manager to assess the same Trader proposal against the research plan. This conditional prompt is part of the ablation; all other upstream evidence, model settings and rating-to-weight rules are shared. The hypothesis is that risk review changes final decision selectivity. Profitability and drawdown benefits require a longer portfolio study and are not assumed.

## 6. Controlled component experiment

Early end-to-end runs revealed different tool coverage: the first run had OHLCV, whereas subsequent runs initially lacked it because yfinance could not open its SQLite cache. Pooling these decisions would confound input failures with risk review. We retain those runs as diagnostics in `diagnostic_run_inventory.csv` and do not use them for the controlled comparison below.

The controlled experiment freezes the four analyst reports, research debate, investment plan and Trader proposal from `risk_full_clean_rep1` for each ticker on 2024-03-28. Both conditions receive the same post-Trader state, verified by SHA-256. The old risk debate, old final decision and all subsequent outcome reflections are excluded. Instrument identity uses the same standard ticker-only fallback in both conditions; portfolio context is unspecified and past memory is empty. Original risk-agent factories, router and Portfolio Manager are reused; the full condition has one round (three risk turns), while the ablation has zero turns. No external data tools run during replay.

Three independent provider-sampled repetitions cover 3 tickers x 2 conditions x 3 trials = 18 cells. Condition order alternates by trial. Different tickers run concurrently, with no shared learning. Model, input and risk-turn invariants are checked before aggregation; incompatible resumes are rejected. Primary metrics are final ratings, the fraction of paired decisions that differ and target weight. Under the existing scoring convention Buy=100%, Overweight=75%, Underweight=50%, Sell=0%; Hold/REVIEW retain the initial weight, zero in this slice. These weights are local scoring assumptions, not the paper's disclosed position-sizing rules.

The statistical unit is one trial's mean over the same three tickers. Sample variance uses denominator n-1 across three trial means. This quantifies model-output variation conditional on one date's frozen evidence; it does not make nine independent market-date observations or estimate uncertainty across regimes.

## 7. Measured ablation results

All 18 cells completed. Every paired input hash and model configuration matched, full runs recorded exactly three risk turns, and no-risk runs recorded zero. The ratings were:

| Ticker | Full trial 1 | Full trial 2 | Full trial 3 | No risk (all trials) |
|---|---|---|---|---|
| AAPL | Sell | Sell | Sell | Underweight |
| GOOGL | Sell | Sell | Underweight | Underweight |
| AMZN | Underweight | Underweight | Underweight | Underweight |

| Trial | Full mean target % | No-risk mean target % | No-risk minus full (pp) | Changed ratings / 3 |
|---|---:|---:|---:|---:|
| 1 | 16.67 | 50.00 | +33.33 | 2 |
| 2 | 16.67 | 50.00 | +33.33 | 2 |
| 3 | 33.33 | 50.00 | +16.67 | 1 |

| Across three trial means | Full | No risk | Paired difference |
|---|---:|---:|---:|
| Mean target / difference (%, pp) | 22.22 | 50.00 | +27.78 |
| Sample variance (pp squared) | 92.59 | 0.00 | 92.59 |
| Sample standard deviation (pp) | 9.62 | 0.00 | 9.62 |

Five of nine ticker-trial pairs (55.6%) had different ratings. Removing risk review increased the average target weight by 27.78 percentage points. In this fixed-input slice, the risk team generally pushed the manager toward Sell for AAPL and GOOGL; AMZN was unchanged. Zero observed variance for the no-risk group is a result from three trials, not a guarantee of deterministic behavior.

The experiment measures downstream behavior. Its one date and fixed upstream text do not estimate CR, AR, Sharpe or MDD for the agent strategy. Native five-session settlement was restored separately, but its raw asset return and benchmark alpha are independent of the model's rating; they are not trading-strategy P&L and are not used as an ablation performance claim. The full 61-session TradingAgents portfolio remains unmeasured.

## 8. Debug diary and reproducibility limits

The inherited HTTP_PROXY/HTTPS_PROXY/ALL_PROXY variables, in both cases, pointed to `127.0.0.1:9` with no listener. Direct endpoint probes worked after ignoring those variables. The experiment subprocesses removed only those proxy variables; no global network setting, model, vendor or VPN was changed. OpenAI-compatible inference then completed normally.

A second failure, `sqlite3.OperationalError: unable to open database file`, came from yfinance's default cookie/time-zone cache. The runner now calls its supported cache-location API with a writable per-run `run_files/yfinance_cache` directory. A native five-session price/alpha fetch then succeeded, and resuming the previous runs settled their pending entries while skipping saved decisions. Yahoo prices and configured FRED calls returned HTTP 200 in direct probes, but historical Yahoo news still raised YFDataException, social requests returned 403/429, and SEC/FRED sometimes raised SSL EOF or timeouts. Fixed snapshots prevent this availability drift between the two controlled conditions, while preserving the source reports' missing-data limitations.

One supplementary run was accidentally started without the ablation flag. Its recorded settings identified it as a control; it was stopped, retained and excluded from ablation statistics. A CSV export also read `raw_return` while the memory parser supplied `raw`, leaving an empty field despite successful settlement. That export now uses the parser's actual key. The Sharpe formula was retained and explicitly documented; regression tests cover varying risk-free rates and a flat portfolio. No Sharpe implementation change is claimed.

Validation comprised 13 focused unittest cases (replay isolation/routing/summary, settled-value export, ticker/date barriers, rating mapping and portfolio metrics), plus two existing graph-route checks called directly because pytest was absent. They pass in the documented environments. This is focused validation, not a claim that every upstream test or live tool passed. Exact sampling reproduction is not guaranteed by the provider. We report no significance test, long-run advantage, causal effect across all market regimes or verified billing total.

## 9. Conclusion and submission status

The technical baseline subset runs from included inputs and yields documented metrics, with clear differences from the paper. The component experiment successfully isolates the risk stage on common upstream evidence: removing it changed 5/9 decisions and increased mean target exposure by 27.78 pp across three stochastic trials (sample SD 9.62 pp). It supports the narrower finding that risk review changed decision selectivity in this slice; it does not establish profitability or drawdown improvement.

The assignment's report, measured modification, repeated-trial statistics, install/run instructions and inspectable artifacts are published in commit `8e6a2ad` on the private branch `qiyan/luna-sentiment-adapter`. The grader still needs repository access. The student's <=15-minute recorded Zoom presentation and link remain outstanding; a speaking guide is provided separately. These student actions are listed in `reports/HUMAN_IN_LOOP.md`.

## References

[1] Xiao, Y., Sun, E., Luo, D., and Wang, W. TradingAgents: Multi-Agents LLM Financial Trading Framework. arXiv:2412.20138. <https://arxiv.org/abs/2412.20138>

[2] Cheng, E. Y.-C., Tseng, C.-J., and Chu, H.-T. Adaptive LLM-based multi-agent systems to enhance quantitative trading performance. PeerJ Computer Science 12:e3630 (2026), Table 3. <https://peerj.com/articles/cs-3630/>. Publisher access returned 403; Table 3 was checked in the author-paper copy at <https://www.researchgate.net/publication/402041844_Adaptive_LLM-based_multi-agent_systems_to_enhance_quantitative_trading_performance>.
