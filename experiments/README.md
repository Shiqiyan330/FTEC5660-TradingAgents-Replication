# Table 1 Backtest

Run from the repository root with an environment that has `pandas`, `numpy`, and `vectorbt`:

```powershell
python experiments/table1_backtest.py --data-dir smoke_test/paper_prices --output-dir smoke_test/table1_results
```

Inputs are `AAPL.csv`, `GOOGL.csv`, `AMZN.csv`, and `DGS3MO.csv`. Stock files contain Yahoo daily OHLCV plus `Adj Close`; DGS3MO is the daily 3-month Treasury constant-maturity series from the Federal Reserve Bank of St. Louis. The runner writes a metrics table, daily equity curves, and a JSON configuration record.

The submission includes the input snapshot and checksums in `experiments/data/table1`, and the corresponding outputs in `experiments/results/table1_baselines`. Recalculate offline in an environment with `vectorbt==1.2.1` (plus its dependencies) using a new output directory:

```powershell
python experiments/table1_backtest.py --data-dir experiments/data/table1 --output-dir tmp/table1_rerun
```

The paper window is 2024-01-01 through 2024-03-29. The available market sessions run from 2024-01-02 through 2024-03-28. Adjusted OHLC is calculated by multiplying raw Open/High/Low by `Adj Close / Close`; Adjusted Close is used to value the portfolio.

MACD uses EMA(12,26,9), entering when MACD is above its signal line. KDJ+RSI uses KDJ(9,3,3) and RSI(14): enter when K crosses above D with K below 30 and RSI below 50; exit when K crosses below D with K above 80 or RSI above 70. ZMR uses the 20-session close z-score, entering at or below -2 and exiting at or above 0. SMA uses the 20/50-session crossover. Buy-and-Hold targets 100% exposure from the first session open. Rule strategies start flat; a close-derived target is filled at the next session open.

Each ticker starts with $100,000. Orders target portfolio exposure and are long-only. Commission is 0 basis points and slippage is 5 basis points per order for liquid U.S. mega-cap stocks at daily frequency. Rating targets for the TradingAgents run are Buy 100%, Overweight 75%, Hold retain the previous target, Underweight 50%, and Sell 0%; REVIEW also retains the previous target.

CR uses final equity relative to initial cash. AR applies the paper's geometric formula using the stated calendar window. Sharpe divides mean daily excess return by the sample standard deviation of daily portfolio returns, then annualizes by `sqrt(252)`; the risk-free rate is the prior available DGS3MO observation. This follows the portfolio-volatility form used in performance measurement. MDD is reported as a positive peak-to-trough percentage. The paper describes the comparator strategies and metric formulas but does not specify their indicator parameters, execution price, position sizing, fees, or slippage.

- Paper: https://arxiv.org/html/2412.20138
- DGS3MO: https://fred.stlouisfed.org/series/DGS3MO

## TradingAgents Table 1 Run

Run the model grid from the repository root in the configured Conda environment. The pilot covers all three tickers on the final paper-window session; running the full command with the same run ID resumes those cells and analyzes the rest of the 61 sessions.

```powershell
python -m experiments.run_tradingagents_table1 --pilot --run-id table1_2024
python -m experiments.run_tradingagents_table1 --run-id table1_2024 --parallel-tickers
```

The parallel runner overlaps AAPL, GOOGL, and AMZN for each date, then waits for all three before moving to the next date. Its shared memory log preserves cross-ticker context, and completed ticker-date cells are skipped when resuming the same run ID. After the full grid, it audits news availability and retries each reported-unavailable Yahoo company/global-news window once. The audit and retry responses are saved to `news_coverage_audit.csv`, `news_retry_results.csv`, and `news_retries/`; supplemental retries do not overwrite first-pass model decisions.

The runner stores yfinance's SQLite cookie cache under the selected output directory at `run_files/yfinance_cache`, so a restricted Windows user-cache path does not block requests. This environment also inherited proxy variables pointing to `127.0.0.1:9` with no listener. Removing those variables for the current PowerShell process restored direct model access; no VPN was required. Do not clear a proxy that is known to be working in another environment.

The model runner writes resumable decision records and full per-cell state logs under `smoke_test/table1_agent_full/`. If the full grid completes, score it with the vectorbt environment:

```powershell
..\vectorbt\.venv\Scripts\python.exe -m experiments.score_tradingagents_table1
```

Scoring produces the combined Table 1 metrics, daily equity curves, rating-to-weight records, executed orders, improvement row, and one offline HTML comparison chart per ticker. The daily decision mapping is Buy 100%, Overweight 75%, Hold retain, Underweight 50%, Sell 0%, and REVIEW retain. A missing model decision is reported and prevents final scoring.

## Risk-Team Ablation

The modification keeps the configured LLMs fixed and removes the three-agent risk debate (aggressive, conservative, and neutral). In the ablated graph, the Trader's proposal goes directly to the Portfolio Manager, whose prompt explicitly says no risk debate occurred. The analyst team, research debate, memory, tools, dates, market data, execution, and scoring stay the same. Use distinct run IDs and output directories so checkpoints and decisions cannot mix:

```powershell
python -m experiments.run_tradingagents_table1 --run-id table1_full --output-dir smoke_test/table1_full --parallel-tickers
python -m experiments.run_tradingagents_table1 --run-id table1_no_risk --output-dir smoke_test/table1_no_risk --parallel-tickers --ablate-risk-management
```

The TradingAgents paper describes the risk team as monitoring exposure and mitigating risk, and attributes its reported drawdown behavior to risk-control debates. It does not report a component-level ablation, so this experiment tests that design claim rather than reproducing a published ablation. A related financial multi-agent study reports lower cumulative return, mean return, and Sharpe after removing agents or collaboration mechanisms; that supports ablation as a useful method but does not establish the expected effect size for TradingAgents. Sources: [TradingAgents](https://arxiv.org/abs/2412.20138), [Adaptive LLM-based Multi-Agent Systems to Enhance Quantitative Trading Performance](https://peerj.com/articles/cs-3630/).

Compare the full and ablated runs with the same scoring script and report CR, AR, Sharpe, and MDD per ticker alongside decision-rating changes. Results are model- and date-window-specific; they estimate the risk team's marginal contribution under this configuration.

## Frozen-input paired risk ablation

Live tool availability differed across the initial end-to-end diagnostic runs. The controlled component experiment therefore reuses the four analyst reports, research debate, research plan and Trader proposal saved by `risk_full_clean_rep1` for 2024-03-28. The committed snapshots are in `experiments/results/risk_replay/inputs`. They deliberately omit the previous risk debate, Portfolio Manager decision and all later outcome reflections. Instrument context is the standard ticker-only fallback, portfolio context is unspecified, and past memory is empty in both conditions.

`run_risk_replay` calls the repository's original risk-agent factories, conditional router and Portfolio Manager. Full runs execute aggressive, conservative and neutral turns, then the Portfolio Manager; no-risk runs call the same Portfolio Manager factory with the existing ablation flag. Both model tiers remain `gpt-6-luna`. The two conditions start from byte-identical state hashes. Three stochastic repetitions alternate which condition runs first; ticker pairs may run concurrently without live data tools or shared learning. Provider-default decoding is used unless explicitly recorded in `settings.llm_kwargs`; no seed guarantee is assumed.

```powershell
conda activate fin-agent-sakura
python -m experiments.run_risk_replay --trials 3
python -m experiments.summarize_risk_replay
python -m unittest experiments.test_risk_replay -v
```

Each completed cell is saved separately under `experiments/results/risk_replay/cells` with its source hash, input hash, models, risk flag, risk-turn count, rating and full decision. Resuming skips compatible completed cells and rejects changed inputs/settings. The frozen inputs retain the source run's missing historical news/social coverage; this evaluates the risk component conditional on those reports, rather than claiming a complete historical Table 1 replication.

Recomputing `summary.json`, `ratings.csv` and `trial_means.csv` is offline and makes no model calls. The summary verifies all 18 expected cells and common input/model/risk-turn invariants before calculating mean, sample variance and standard deviation across the three trial means. To obtain genuinely new random trials, choose a fresh `--output` directory rather than reusing the completed one.
