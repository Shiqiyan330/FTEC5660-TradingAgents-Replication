# News-inclusive rerun: execution record

The user requested a news-inclusive rerun of all experiments in the current report. This run preserves the same three tickers (AAPL, GOOGL, AMZN), decision date (2024-03-28), configured model identifiers and primary risk-debate ablation. A separate chat owns the 61-session portfolio run; the one-date replay below does not substitute for that run.

## Verified inputs and completed work

- Benzinga historical access succeeded for the original 2024-03-21 through 2024-03-28 news window. The frozen corpus in `experiments/data/news_20240328` contains 20 AAPL, 20 GOOGL, 18 AMZN, and 10 global articles. Articles may overlap across streams; these counts are not counts of unique independent events.
- The corpus stores article IDs, titles, source URLs, publication/update timestamps, tags, and excerpts limited to 20 words. Full raw API responses and credentials remain local. The manifest records checksums and the exclusive cutoff of 2024-03-29 00:00 UTC. Articles published outside the window or updated after the cutoff were excluded when the corpus was created. The API does not prove historical text vintages beyond its returned timestamps.
- This is a capped news sample, not exhaustive historical coverage. The initial collection used capped daily requests without pagination; later additions to the shared vendor support a paginated fallback but do not alter this frozen corpus.
- The vendor verifies each snapshot checksum, rejects requests outside its available date window, and records actual article access in the run's `news_snapshot_access.jsonl`. The freeze step requires recorded nonempty company and global news access before it exports post-Trader states.
- All 15 technical-baseline rows were recomputed in `experiments/results/table1_baselines_news`. They match the previous results: those strategies depend on prices and rates, not news.
- Six Benzinga date/filter/fallback/sanitization/snapshot checks passed by direct invocation with isolated temporary directories. Thirteen existing focused unittest cases passed in the Conda and vectorbt environments.

## Execution status

The first concurrent source attempt, `news_full_20240328`, was stopped after AAPL and GOOGL failed with the gateway's concurrency-limit error. No completed source states from that attempt are counted. Reddit 403/429 and intermittent FRED SSL errors remain separate availability limitations; adding financial news does not restore historical social posts.

The replacement source run serializes tickers and graph nodes and increases only the SDK retry budget. Models, prompts, dates and news snapshot remain fixed. Automatic execution approval repeatedly disconnected before launching this replacement process. It has not run, and no news-inclusive agent result is claimed yet. The existing PDF therefore still reports the earlier news-unavailable experiment, not a completed news-inclusive rerun.

## Resume the prepared run

Run from the repository root after execution approval is functioning. Remove the listed proxy variables only if they still point to the known closed local port; do not change a working proxy.

```powershell
conda activate fin-agent-sakura
$proxyNames = @('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy')
foreach ($name in $proxyNames) { Remove-Item "Env:\$name" -ErrorAction SilentlyContinue }
$env:TRADINGAGENTS_LLM_MAX_RETRIES = '8'
python -m experiments.run_tradingagents_table1 --pilot --data-dir experiments/data/table1 --run-id news_full_serial_20240328 --output-dir smoke_test/news_full_serial_20240328 --news-vendor benzinga --news-snapshot-dir experiments/data/news_20240328 --graph-max-concurrency 1
python -m experiments.freeze_risk_replay_inputs
python -m experiments.run_risk_replay --inputs experiments/results/risk_replay_news/inputs --output experiments/results/risk_replay_news/cells --trials 3
python -m experiments.summarize_risk_replay --root experiments/results/risk_replay_news
```

After completion, verify all 18 paired cells, identical input hashes within each pair, positive news access and three versus zero risk turns. Save the model/provider/default-decoding settings and retry policy in the new manifest. Compare the new statistics with the original news-unavailable results without pooling the two datasets or claiming a causal news effect from independently regenerated upstream reports. Update and render the report PDF, submission audit, presentation guide and source-change audit using the observed results, then commit and push that final stage.
