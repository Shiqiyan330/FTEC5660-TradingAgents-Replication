# Table 1 Backtest

Run from the repository root with an environment that has `pandas`, `numpy`, and `vectorbt`:

```powershell
python experiments/table1_backtest.py --data-dir smoke_test/paper_prices --output-dir smoke_test/table1_results
```

Inputs are `AAPL.csv`, `GOOGL.csv`, `AMZN.csv`, and `DGS3MO.csv`. Stock files contain Yahoo daily OHLCV plus `Adj Close`; DGS3MO is the daily 3-month Treasury constant-maturity series from the Federal Reserve Bank of St. Louis. The runner writes a metrics table, daily equity curves, and a JSON configuration record.

The paper window is 2024-01-01 through 2024-03-29. The available market sessions run from 2024-01-02 through 2024-03-28. Adjusted OHLC is calculated by multiplying raw Open/High/Low by `Adj Close / Close`; Adjusted Close is used to value the portfolio.

MACD uses EMA(12,26,9), entering when MACD is above its signal line. KDJ+RSI uses KDJ(9,3,3) and RSI(14): enter when K crosses above D with K below 30 and RSI below 50; exit when K crosses below D with K above 80 or RSI above 70. ZMR uses the 20-session close z-score, entering at or below -2 and exiting at or above 0. SMA uses the 20/50-session crossover. Buy-and-Hold targets 100% exposure from the first session open. Rule strategies start flat; a close-derived target is filled at the next session open.

Each ticker starts with $100,000. Orders target portfolio exposure and are long-only. Commission is 0 basis points and slippage is 5 basis points per order for liquid U.S. mega-cap stocks at daily frequency. Rating targets for the TradingAgents run are Buy 100%, Overweight 75%, Hold retain the previous target, Underweight 50%, and Sell 0%; REVIEW also retains the previous target.

CR uses final equity relative to initial cash. AR applies the paper's geometric formula using the stated calendar window. Sharpe uses daily excess returns against the prior available DGS3MO observation, annualized by `sqrt(252)`. MDD is reported as a positive peak-to-trough percentage. The paper describes the comparator strategies and metric formulas but does not specify their indicator parameters, execution price, position sizing, fees, or slippage.

- Paper: https://arxiv.org/html/2412.20138
- DGS3MO: https://fred.stlouisfed.org/series/DGS3MO
