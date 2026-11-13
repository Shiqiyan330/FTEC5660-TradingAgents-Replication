# Student presentation guide (target: 10-12 minutes)

Record your own Zoom presentation, then submit an accessible recording link. This file is a speaking and demo guide, not a recording or evidence that the video requirement is complete.

## 0:00-1:30 — Project and target

Introduce TradingAgents and show the analyst -> bull/bear research -> Trader -> three-viewpoint risk debate -> Portfolio Manager flow. Explain that the homework permits a defined subset. State the two measured targets: Q1 2024 technical-baseline reconstruction and a fixed-input risk-stage behavioral ablation on 2024-03-28 across AAPL, GOOGL and AMZN.

## 1:30-3:00 — Setup and fairness

Show the report setup and machine-readable manifest. Both tiers use gpt-6-luna through the same configured gateway. This is different from the paper's gpt-4o/o1-era backbone. Do not claim matching the original paper's model or exact Table 1. Agent runs use fin-agent-sakura; baseline scoring needs vectorbt in the documented separate environment. Keys remain local.

## 3:00-4:30 — Reproduction results

Show the baseline result table and one disagreement, such as AAPL Buy & Hold -8.30% versus paper -5.23%. Explain next-session-open execution, warm-up, 5 bps slippage, and the paper's unstated parameters. Mention the CR/AR arithmetic inconsistency without claiming to know its cause. Open `experiments/results/table1_baselines/table1_metrics.csv` as measured output.

## 4:30-7:00 — Modification and measured impact

Explain why risk review is a meaningful module: the original paper attributes risk control to it, and related literature tests risk-agent removal. Show the conditional routing code. Then show `experiments/results/risk_replay/inputs/AAPL.json`, the paired cell hashes and `summary.json`.

The shared post-Trader state prevents live data failures from differing between conditions. Full has three risk turns; ablation has zero, while the Portfolio Manager remains. Three random repetitions give 18 cells. No-risk minus full target weight is +33.33, +33.33 and +16.67 pp, mean +27.78 pp and sample SD 9.62 pp. Ratings differ in 5/9 pairs. Explain that the trial, not each correlated ticker, is the statistical unit. These are behavior/position-target metrics, not verified investment gains.

## 7:00-9:00 — Demo without API spending

From the repository root with fin-agent-sakura active:

```powershell
python -m experiments.summarize_risk_replay
python -m unittest experiments.test_risk_replay -v
```

The summary validates 18 cells and exact input/config/routing invariants, then recomputes means and sample variances offline. A new hosted-model run requires a fresh output directory and uses stochastic provider inference. Do not rerun live inference during the recording unless you want the time and API cost.

## 9:00-11:00 — Debug diary and conclusions

Describe the dead 127.0.0.1:9 proxy and yfinance SQLite cache permission issue. Both were addressed without a VPN or changing vendor/model. Historical news/social coverage and intermittent SSL errors remain limitations. Earlier mixed-availability trials were retained as diagnostics; a misconfigured supplemental control was explicitly excluded.

Conclude: the baseline subset is runnable but does not exactly recover published numbers; conditional risk review measurably changed ratings/exposure in this slice. More market dates and a full portfolio evaluation are needed before any profitability/drawdown claim. Show the repository branch and report link.

## Before submitting

Ensure your microphone/audio is clear, the video is at most 15 minutes, the recording link opens for the grader, the private repository is accessible, and no terminal exposes API keys. Add your student ID through the course submission form if needed. Verify the recording by opening it yourself; do not claim the guide satisfies the video requirement.
