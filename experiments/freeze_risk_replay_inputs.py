"""Export completed news-inclusive upstream states for paired risk replay."""
import argparse
import hashlib
import json
from pathlib import Path

from experiments.run_risk_replay import PREFIX_KEYS, TICKERS


def freeze(source, output, run_id):
    bundles = {}
    access = [json.loads(line) for line in (source / 'news_snapshot_access.jsonl').read_text(encoding='utf-8').splitlines()]
    for ticker in TICKERS:
        if not any(a['ticker'] == ticker and a['article_ids'] for a in access):
            raise ValueError(f'No recorded company-news consumption for {ticker}')
        path = source / 'run_files/results/backtest' / run_id / ticker / 'TradingAgentsStrategy_logs/full_states_log_2024-03-28.json'
        data = path.read_bytes()
        state = json.loads(data)
        if any(not state.get(k) for k in PREFIX_KEYS):
            raise ValueError(f'Incomplete upstream reports for {ticker}')
        bundles[ticker] = {'source_run_id':run_id,
            'source_state_sha256':hashlib.sha256(data).hexdigest(),
            'source_run_settings':state['run_settings'],
            'state':{k:state[k] for k in ('company_of_interest','trade_date',*PREFIX_KEYS)}}
    if not any(a['ticker'] == 'GLOBAL' and a['article_ids'] for a in access):
        raise ValueError('No recorded global-news consumption')
    output.mkdir(parents=True,exist_ok=True)
    for ticker,bundle in bundles.items():
        path = output / f'{ticker}.json'
        if path.exists():
            raise ValueError(f'Refusing to overwrite frozen input {path}')
        path.write_text(json.dumps(bundle,ensure_ascii=False,indent=2) + '\n',encoding='utf-8')
    print('Frozen complete post-Trader states with verified company/global news access:', ', '.join(bundles))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('smoke_test/news_full_serial_20240328'))
    parser.add_argument('--output',type=Path,default=Path('experiments/results/risk_replay_news/inputs'))
    parser.add_argument('--run-id',default='news_full_serial_20240328')
    args=parser.parse_args()
    freeze(args.source,args.output,args.run_id)
