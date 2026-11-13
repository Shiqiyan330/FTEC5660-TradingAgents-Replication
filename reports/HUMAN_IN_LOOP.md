# Human-in-the-Loop / Submission Checklist

## Pending student actions

1. **Give the grader repository access.** The repository is private, so its link alone will not grant access. Sign in to GitHub as `Shiqiyan330`, open the replication repository, then use **Settings > Collaborators** (or **Collaborators and teams**) to invite the instructor/TA by their GitHub username with read access. After they accept, ask them to confirm they can open branch `qiyan/luna-sentiment-adapter`. Keep the repository private unless the course explicitly requires public access. The source project remains publicly available at TauricResearch/TradingAgents.

2. **Record the presentation and provide its link.** Use [the 10-12 minute speaking/demo guide](presentation_guide.md). In Zoom, start a meeting, share the repository/report/results, and record to the computer or the university Zoom account. Keep the video under 15 minutes, make sure no terminal or screen shows API credentials, and upload it to a university-approved location. Set link permissions so the grader can view it, then test the link in a private browser window or another account. Paste the working link into the course submission form. No recording is claimed to have been made by the student.

3. **Complete the LMS submission.** Paste the repository branch link and report path below, then add the recording link and student ID if required by the course form. Submit only after testing the repository and video permissions.

   - Repository branch: `https://github.com/Shiqiyan330/FTEC5660-TradingAgents-Replication/tree/qiyan/luna-sentiment-adapter`
   - Report: `reports/reproducibility_report.pdf`
   - Presentation recording: add your tested Zoom recording link
   - Student ID: add only if requested

## Published payload

Commits `8e6a2ad`, `2d87018`, `8c6da23`, and `658896b` were verified on `Shiqiyan330/FTEC5660-TradingAgents-Replication`, branch `qiyan/luna-sentiment-adapter`. They contain the reproduction code and tests, three model-generated frozen input snapshots, all paired ablation outputs, baseline data and metrics, diagnostics, README instructions, report, submission audit, and upstream-change audit. API credentials and local cookie/cache databases are excluded.

The student confirmed ownership of the repository and explicitly authorized this payload before publication.

## Resolved without further action

- You authorized sufficient hosted-model budget and stochastic repeated trials in this chat.
- You confirmed ownership of the private replication repository and authorized the specified experiment payload and report for publication to the coursework branch.
- You authorized autonomous diagnosis of Yahoo, StockTwits, Reddit and FRED failures while preserving the model and sources.
- The inherited proxy variables all pointed to the closed local port `127.0.0.1:9`; they were removed only inside experiment subprocesses. No global proxy change or VPN was needed for the successful model and price requests.
- yfinance could not open its default SQLite cookie/cache database. The experiment runner now uses the output directory's writable `run_files/yfinance_cache` folder. Native settlement succeeded after this correction without regenerating the saved decisions.
- Historical news/social requests still return provider errors or HTTP 403/429, and SEC/FRED have intermittent SSL errors. The controlled component experiment freezes the same saved reports for both conditions rather than changing suppliers or silently filling missing evidence.
- Exploratory end-to-end decisions with different input availability are retained as diagnostics, not pooled with the common-input component experiment. One supplemental run was stopped after discovering a missing ablation CLI flag; it is not counted as an ablation.
