"""Run the news-inclusive three-ticker window and paired risk ablation with DeepSeek."""
import argparse
import os
from pathlib import Path


def configure():
    # Process-only overrides: never send this provider's key to the previous gateway.
    for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        os.environ.pop(key,None)
    settings = {
        'LLM_PROVIDER':'deepseek','QUICK_THINK_PROVIDER':'deepseek','DEEP_THINK_PROVIDER':'deepseek',
        'QUICK_THINK_LLM':'deepseek-flash','DEEP_THINK_LLM':'deepseek-flash',
        'LLM_BACKEND_URL':'https://api.deepseek.com',
        'QUICK_THINK_BACKEND_URL':'https://api.deepseek.com',
        'DEEP_THINK_BACKEND_URL':'https://api.deepseek.com',
        'LLM_MAX_RETRIES':'5','MAX_TOKENS':'8192',
    }
    for key,value in settings.items():
        os.environ['TRADINGAGENTS_'+key]=value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('source','replay'),required=True)
    args=parser.parse_args()
    configure()
    run_id='deepseek_news_20240328_ds'
    source=Path('smoke_test')/run_id
    target=Path('experiments/results/risk_replay_deepseek_news_ds')
    if args.phase=='source':
        from experiments.run_tradingagents_table1 import run
        result=run(Path('experiments/data/table1'),source,run_id,True,
                   news_vendor='benzinga',news_snapshot_dir=Path('experiments/data/news_20240328'),
                   graph_max_concurrency=1)
        if result['missing_cells']:
            raise SystemExit(2)
    else:
        from experiments.freeze_risk_replay_inputs import freeze
        from experiments.run_risk_replay import TICKERS, run
        missing_states = [
            str(source/'run_files/results/backtest'/run_id/ticker/
                'TradingAgentsStrategy_logs/full_states_log_2024-03-28.json')
            for ticker in TICKERS
            if not (source/'run_files/results/backtest'/run_id/ticker/
                    'TradingAgentsStrategy_logs/full_states_log_2024-03-28.json').is_file()
        ]
        if missing_states:
            paths = '\n'.join(f'  - {path}' for path in missing_states)
            raise SystemExit(
                'Cannot start replay: the source phase has not produced all three '
                f'completed states. Finish --phase source first. Missing:\n{paths}'
            )
        if not (target/'inputs/AAPL.json').exists():
            freeze(source,target/'inputs',run_id)
        run(target/'inputs',target/'cells',3,workers=3)


if __name__=='__main__':
    main()
