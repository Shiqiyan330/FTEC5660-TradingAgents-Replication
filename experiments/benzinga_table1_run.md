# Benzinga Table 1 run (2026-11-13)

Paper window: 2024-01-01 to 2024-03-29, comprising 61 market sessions (2024-01-02 to 2024-03-28), three tickers (AAPL, GOOGL, AMZN) and 183 model decisions.

## Authenticated API probes

| Provider | Probe | Observed result |
| --- | --- | --- |
| Benzinga | Historical AAPL news, 2024-03-28 | HTTP 200, articles returned |
| Benzinga | GOOGL / GOOG / AMZN ticker filters (also current AMZN) | HTTP 200, empty arrays |
| Benzinga | Unfiltered news on 2024-03-28 | Pages 0 and 1 each returned 25 distinct articles; page 2 was empty. Articles include explicit AMZN and GOOGL tags. |
| Finnhub | AAPL news, 2024-03-27 to 2024-03-28 | HTTP 200, empty array |
| Finnhub | AAPL news, 2026-11-10 to 2026-11-12 | HTTP 200, 195 records |
| Finnhub | Historical social sentiment | HTTP 403: no access to the resource |
| Alpha Vantage | Historical NEWS_SENTIMENT | HTTP 200, Information notice requiring premium access |

The keys remain in the ignored environment file. Benzinga is the first provider with observed historical articles. When a ticker query is empty, the adapter paginates the same provider's global daily feed and selects articles whose stock tags explicitly match the ticker. This was verified with the configured key; it avoids interpreting the empty ticker-filtered arrays as an absence of news.

## Protocol

Both LLM tiers retain the configured gpt-6-luna model. All four analysts and the risk team remain enabled. The three tickers run concurrently within each date, preserving the existing date barrier and memory rules. A separate run ID and output directory preserve the earlier Yahoo pilot and partial decisions.

Benzinga's RFC 2822 timestamps are normalized to UTC, using the project's existing date-window convention. Undated historical articles, future articles and revisions later than the decision date are excluded. Historical API access does not establish that the archive is a complete point-in-time vintage. The configured samples remain capped at 20 company and 10 global articles per window. Raw successful responses are cached under run_files/cache/benzinga.

Benzinga supplies news to the news and sentiment analysts. It does not supply social-media posts; historical Reddit/StockTwits limitations remain explicit in the existing analyst reports.

The inherited proxy variables pointed to an inactive 127.0.0.1:9 endpoint. Direct probes succeeded. Only the experiment process clears those proxy variables.

## Commands

Run from the repository with D:/anaconda3/envs/fin-agent-sakura/python.exe:

```powershell
python -m experiments.audit_benzinga_table1 --output-dir smoke_test/table1_benzinga_20261113
python -m experiments.run_tradingagents_table1 --data-dir experiments/data/table1 --output-dir smoke_test/table1_benzinga_20261113 --run-id table1_benzinga_20261113 --parallel-tickers --news-vendor benzinga
..\vectorbt\.venv\Scripts\python.exe -m experiments.score_tradingagents_table1 --data-dir experiments/data/table1 --decision-file smoke_test/table1_benzinga_20261113/decision_cells.csv --baseline-dir experiments/results/table1_baselines --output-dir smoke_test/table1_benzinga_20261113/scored
```

Preflight checks all 244 news windows (183 company, 61 global), requiring no empty or failed windows. Completion requires 183 unique dated decisions, full state logs, a news coverage audit and final scoring. Process startup alone does not establish completion.

## Sources

- [Benzinga News API](https://docs.benzinga.com/api-reference/news-api/get-news-items)
- [Finnhub company news](https://finnhub.io/docs/api/company-news)
- [Finnhub social sentiment](https://finnhub.io/docs/api/social-sentiment)
- [Alpha Vantage NEWS_SENTIMENT](https://www.alphavantage.co/documentation/)

