"""Freeze dated Benzinga headlines and short excerpts for the news-inclusive rerun."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html import unescape
import json
from pathlib import Path
import re

from dotenv import load_dotenv
from tradingagents.dataflows.config import run_config
from tradingagents.dataflows.vendors.benzinga.news import _collect_news


def prepare(output, cache):
    if (output / 'manifest.json').exists():
        raise ValueError('Snapshot exists; use it unchanged or choose a new output directory.')
    output.mkdir(parents=True, exist_ok=True)
    manifest = {'vendor': 'benzinga', 'api_url': 'https://api.benzinga.com/api/v2/news',
                'start_date': '2024-03-21', 'end_date': '2024-03-28',
                'cutoff_utc_exclusive': '2024-03-29T00:00:00Z',
                'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                'selection': 'latest 20 company / 10 global articles after UTC publication and update filtering; daily fetch cap 20 / 10, no pagination; not exhaustive',
                'excerpt_words_max': 20, 'files': {}}

    def collect(ticker):
        limit = 20 if ticker else 10
        with run_config({'data_cache_dir': str(cache.resolve())}):
            articles = _collect_news(ticker, manifest['start_date'], manifest['end_date'], limit)
        if not articles:
            raise ValueError(f'No historical news for {ticker or "GLOBAL"}')
        selected = []
        for article in articles:
            item = {k: article.get(k) for k in ('id', 'title', 'created', 'updated', 'url', 'stocks')}
            plain = unescape(re.sub(r'<[^>]+>', ' ', article.get('teaser') or article.get('body') or ''))
            item['teaser'] = ' '.join(plain.split()[:20])
            selected.append(item)
        name = f'{ticker or "GLOBAL"}.json'
        data = (json.dumps(selected, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        (output / name).write_bytes(data)
        return name, {'article_count': len(selected), 'sha256': hashlib.sha256(data).hexdigest()}

    with ThreadPoolExecutor(max_workers=4) as pool:
        manifest['files'] = dict(pool.map(collect, ('AAPL', 'GOOGL', 'AMZN', '')))
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('experiments/data/news_20240328'))
    parser.add_argument('--cache', type=Path, default=Path('smoke_test/news_fetch_cache'))
    args = parser.parse_args()
    prepare(args.output, args.cache)
