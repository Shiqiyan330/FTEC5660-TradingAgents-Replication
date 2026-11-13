# Changes Against the Paper Repository

## Comparison base

This audit compares the coursework source snapshot at `2d87018` with the checked-out upstream base `9fa1196fffbcfd9de5146d2dd2869df84ab99838`. The snapshot is the published experiment/report payload before adding this audit document. The base is the local `origin/main` commit used when the reproduction branch was created. The comparison contains 65 tracked paths: 4,602 text-line additions, 400 deletions, and one binary PDF. Commits `8e6a2ad`, `2d87018`, and `8c6da23` publish the experiment/report payload, its status update, and this upstream-change audit respectively.

The differences group into runtime adaptations, reproduction and ablation tooling, tests, data/results, and coursework documentation. They do not represent 65 changes to the upstream trading framework.

## Runtime changes

| Upstream path | Difference | Role in the coursework |
|---|---|---|
| `tradingagents/agents/post_screen.py` | Replaces the separate TypeSafe/Jev HTTP client with structured screening through the configured model client. It validates stance probabilities, uses concurrent screening, and leaves posts unscreened if model screening fails. Probabilities are compatibility estimates, not Jev-calibrated confidence. | Provider/model compatibility adaptation; common to both experimental conditions. |
| `tradingagents/agents/analysts/sentiment_analyst.py` | Passes the sentiment analyst's configured LLM client into the StockTwits and Reddit post screen. | Connects the compatibility adapter to the existing social feeds. |
| `tradingagents/default_config.py` | Adds `risk_management_enabled`, defaulting to `True`. | Keeps the published graph behavior as the default and exposes the ablation switch. |
| `tradingagents/graph/setup.py` | Creates the risk debate nodes only when enabled; when disabled, routes Trader directly to Portfolio Manager. | Implements the isolated risk-team ablation. |
| `tradingagents/graph/trading_graph.py` | Passes the risk-management setting into graph construction. | Carries the experiment configuration into the workflow. |
| `tradingagents/agents/managers/portfolio_manager.py` | Makes the risk debate input and prompt conditional. The no-risk prompt explicitly says that no debate occurred while retaining the Portfolio Manager. | Prevents the ablated manager from treating an absent debate as evidence. |
| `.env.example` | Removes the obsolete TypeSafe/Jev environment variables. | Keeps the sample configuration aligned with the screening adapter. |

The sentiment screening adapter is a reproduction-environment adaptation, not the experimental ablation. The ablation changes only whether the three-agent risk debate runs; the same frozen upstream evidence, model settings, and Portfolio Manager are used in both conditions. The configured experiment model is `gpt-6-luna` for both tiers through the recorded OpenAI-compatible gateway; the gateway's underlying model identity is not independently verified, and the paper used different models.

## Experiment code

The following new scripts implement the selected measurement and are separate from the upstream runtime:

- `experiments/table1_backtest.py` calculates the five technical strategies from included daily price and rate snapshots with explicit local execution assumptions.
- `experiments/run_tradingagents_table1.py` runs and resumes the three-ticker decision grid, with same-date ticker concurrency, a date barrier for shared memory, saved state logs, and source-coverage diagnostics.
- `experiments/score_tradingagents_table1.py` maps saved ratings to target weights and calculates the Table 1 portfolio metrics.
- `experiments/run_risk_replay.py` compares full versus no-risk decisions from the same saved post-Trader evidence.
- `experiments/summarize_risk_replay.py` validates the complete paired-cell set and calculates ratings, target-weight differences, and trial-level dispersion offline.

Supporting tests are `experiments/test_table1_backtest.py`, `experiments/test_tradingagents_table1.py`, `experiments/test_parallel_tradingagents_table1.py`, and `experiments/test_risk_replay.py`. `tests/test_risk_management_ablation.py` checks the enabled and bypass graph routes.

## Data and result artifacts

- `experiments/data/table1/` contains the AAPL, GOOGL, AMZN, and DGS3MO input snapshots plus provenance and SHA-256 checksums.
- `experiments/results/table1_baselines/` contains the scoring configuration, metrics, and equity curves for 15 technical baseline rows.
- `experiments/results/risk_replay/inputs/` contains three frozen upstream report bundles for 2024-03-28; `cells/` contains 18 completed paired model decisions; the manifest and summary CSV/JSON files preserve model settings, hashes, ratings, and trial statistics.
- `experiments/results/diagnostic_run_inventory.csv` records exploratory runs excluded from the controlled comparison.

These files are experiment evidence, not new upstream application code. Local `output/`, `smoke_test/`, and `tmp/` directories are not part of the published branch.

## Tests and coursework documentation

- `tests/test_post_screen.py` replaces tests for the TypeSafe API contract with tests for the configured-model adapter, its probability validation, and its unscreened fallback. `tests/test_reddit_fallback.py` updates the corresponding fallback label.
- `AGENTS.md` adds repository-specific human-in-the-loop workflow guidance; it does not change runtime behavior.
- `README.md`, `experiments/README.md`, and `REPLICATION_STATUS.md` document installation, commands, assumptions, results, and limitations.
- `reports/` contains the reproducibility report, PDF builder, submission audit, presentation guide, human checklist, and this source-change audit. `.gitignore` allows these named deliverables while continuing to ignore other generated reports; `.gitattributes` marks PDFs binary.

## Scope and limitations

The coursework changes the existing agent graph only to support the risk-team switch and to adapt social-post screening to the configured model client. Other new Python modules implement measurement, replay, validation, and reporting. Yahoo Finance, StockTwits, Reddit, SEC, and FRED remain the configured data sources; this branch does not silently replace vendors. Historical news/social gaps and intermittent SSL or access errors are documented, and the controlled risk replay holds the saved upstream evidence fixed across conditions.

The measured agent ablation concerns final ratings and target exposure on one date with three stochastic repetitions. It does not report an agent-portfolio CR, AR, Sharpe, or MDD for the complete 61-session window. The assignment permits a clearly defined subset; the report presents the 15 technical baseline rows and fixed-input risk behavior as that subset and does not claim exact full-paper performance reproduction.
