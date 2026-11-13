# Reproducibility assignment audit

Checked against `C:/Users/QiyanShi/Downloads/Reproducibility.pdf`, pages 1-3, on 2026-11-13. This is a requirement-by-requirement status record, not a claim that every submission item is complete.

| Requirement | Current evidence | Status |
|---|---|---|
| Public agentic source with runnable multi-step pipeline | TauricResearch/TradingAgents; saved analyst, research, Trader, risk and manager states | Satisfied for chosen source; student fork is private |
| Own measured result/behavior compared with reported claim | 15 technical-baseline rows over 61 sessions, paper comparison CSV; final risk-review behavior tested on common post-Trader evidence | Satisfied for documented subset; paper's agent return/MDD not recovered |
| Small isolated modification with measurable impact | Risk debate on/off, Portfolio Manager retained with explicit condition prompt; 18 common-input paired cells | Satisfied locally |
| 3-5 stochastic trials and mean/variance | Three repetitions, 3 tickers and 2 conditions; trial mean and sample variance in risk_replay/summary.json | Satisfied locally; statistical unit and one-date limit documented |
| Environment, data, compute and keys | Report section 2, manifest, baseline input checksums; no GPU needed; keys local | Satisfied locally; billing not captured |
| Model/provider/base URL/decoding and prompt changes | Manifest has exact configured identifiers and sanitized base URL; defaults explicitly marked; report documents original-paper difference and no-risk prompt | Satisfied for configured endpoint; underlying gateway model identity not independently verified |
| Metric definitions and your numbers vs paper | Report sections 3-4, table1_metrics.csv with CR/AR/Sharpe/MDD; assumptions distinguished from paper | Satisfied for technical baselines, not full agent portfolio |
| Modification and results after modification | Report sections 5-7; 5/9 changed ratings; target exposure difference +27.78 pp, sample SD 9.62 pp | Satisfied locally; no profitability or drawdown claim |
| Debug diary, conclusions and limits | Report sections 8-9, diagnostic inventory; proxy, cache, missing news and mistaken supplemental control recorded | Satisfied locally |
| Brief report <=10 pages | reports/reproducibility_report.pdf, 5 A4 pages; extracted and visually reviewed | Satisfied locally |
| README with install/run steps | Root README points to experiments/README; committed-snapshot paths and offline summary commands supplied | Satisfied locally; pending publication |
| Reviewable changes in commits | Existing baseline/runner/ablation commits through 2f303f3; coursework payload commit 8e6a2ad is pushed to the target branch | Satisfied |
| No secrets/API keys committed | Local .env untracked; candidate files checked against configured secret values; SQLite cookie caches excluded from candidate payload | Checked for selected payload; recheck before commit |
| GitHub submission link accessible | Private Shiqiyan330/FTEC5660-TradingAgents-Replication; commit 8e6a2ad is pushed to qiyan/luna-sentiment-adapter | Pending confirmation that the grader has access |
| <=15-minute recorded Zoom presentation and link | reports/presentation_guide.md provides a 10-12 minute script/demo plan | Not complete: student recording/link required |

## Verification performed

- Recalculated the 15 baseline rows from the included data snapshot with vectorbt; no model calls.
- Ran 13 focused unittest cases across the Conda and vectorbt environments, plus two original graph routing checks directly; all passed. Did not claim the entire upstream pytest suite passed.
- Completed 18 hosted-model replay cells, with common input hashes and recorded model configuration. The offline summarizer rejects missing/duplicate/mismatched cells and validates three full risk turns versus zero ablated turns.
- Rendered the five-page PDF to PNG and reviewed every page for clipped text/tables and bad page breaks.
- Preserved live-tool diagnostics separately. End-to-end runs with input failures and the mistaken supplemental control were not pooled with the controlled replay.

## Outstanding human actions

See HUMAN_IN_LOOP.md for private-repository grader access, the student recording/link and student ID if required. A speaking guide does not substitute for a presentation recording.
