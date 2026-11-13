# Human-in-the-Loop / Submission Checklist

## Pending student actions

1. **Give the grader repository access.** The verified repository is private. Confirm that the instructor/TA can open the submitted branch or provide access through your preferred submission workflow. The source project remains publicly available at TauricResearch/TradingAgents.

2. **Record the presentation and provide its link.** The assignment requires a recorded Zoom presentation of at most 15 minutes. A speaking/demo guide accompanies the report. No recording is claimed to have been made by the student.

3. **Add your student ID if the course submission needs it.** Do not invent an ID or upload the report under another student's identity.

## Publishing authorization

The student confirmed ownership of `Shiqiyan330/FTEC5660-TradingAgents-Replication` and explicitly authorized publishing the code, tests, three model-generated frozen input snapshots, ablation outputs, baseline artifacts and report to branch `qiyan/luna-sentiment-adapter`. Configured secret values are excluded. The initial automatic review rejected the nonpublic payload before this explicit confirmation; publication is now proceeding under the student's authorization.

## Resolved without further action

- You authorized sufficient hosted-model budget and stochastic repeated trials in this chat.
- You confirmed ownership of the private replication repository and authorized the specified experiment payload and report for publication to the coursework branch.
- You authorized autonomous diagnosis of Yahoo, StockTwits, Reddit and FRED failures while preserving the model and sources.
- The inherited proxy variables all pointed to the closed local port `127.0.0.1:9`; they were removed only inside experiment subprocesses. No global proxy change or VPN was needed for the successful model and price requests.
- yfinance could not open its default SQLite cookie/cache database. The experiment runner now uses the output directory's writable `run_files/yfinance_cache` folder. Native settlement succeeded after this correction without regenerating the saved decisions.
- Historical news/social requests still return provider errors or HTTP 403/429, and SEC/FRED have intermittent SSL errors. The controlled component experiment freezes the same saved reports for both conditions rather than changing suppliers or silently filling missing evidence.
- Exploratory end-to-end decisions with different input availability are retained as diagnostics, not pooled with the common-input component experiment. One supplemental run was stopped after discovering a missing ablation CLI flag; it is not counted as an ablation.
