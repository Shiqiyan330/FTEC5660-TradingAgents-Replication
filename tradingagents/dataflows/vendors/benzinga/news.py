"""Benzinga historical company and global news."""

from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
import hashlib
import json
import os
from pathlib import Path
import re
import time
from threading import Lock
from uuid import uuid4

import requests

from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.date_window import in_window, to_utc
from tradingagents.dataflows.errors import VendorNotConfiguredError, VendorUnavailableError

API_URL = "https://api.benzinga.com/api/v2/news"
_ACCESS_LOCK = Lock()


def _fetch_daily_news(ticker: str, news_date: str, limit: int, *, paginate: bool = False) -> tuple[dict, ...]:
    config = get_config()
    suffix = "_all" if paginate else ""
    cache = Path(config["data_cache_dir"]) / "benzinga" / f"{ticker or 'GLOBAL'}_{news_date}_{limit}{suffix}.json"
    if cache.exists():
        return tuple(json.loads(cache.read_text(encoding="utf-8")))
    if config.get("cache_only_non_fred"):
        raise VendorUnavailableError(f"Benzinga cache missing for {ticker or 'GLOBAL'} on {news_date}.")
    api_key = os.getenv("BENZINGA_API_KEY")
    if not api_key:
        raise VendorNotConfiguredError("BENZINGA_API_KEY environment variable is not set.")

    params = {
        "date": news_date, "pageSize": str(limit), "token": api_key,
        "sort": "created:desc", "displayOutput": "full",
    }
    if ticker:
        params["tickers"] = ticker

    payload = []
    for page in range(100 if paginate else 1):
        params["page"] = page
        for attempt in range(3):
            try:
                response = requests.get(API_URL, params=params, headers={"Accept": "application/json"}, timeout=20)
            except requests.RequestException:
                if attempt < 2:
                    time.sleep(attempt + 1)
                    continue
                raise VendorUnavailableError("Benzinga news request failed.") from None
            if response.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                break
            time.sleep(attempt + 1)
        if response.status_code != 200:
            raise VendorUnavailableError(f"Benzinga news request failed (HTTP {response.status_code}).")

        try:
            batch = response.json()
        except ValueError as exc:
            raise VendorUnavailableError("Benzinga returned an invalid news response.") from exc
        if not isinstance(batch, list) or any(not isinstance(item, dict) for item in batch):
            raise VendorUnavailableError("Benzinga returned an unexpected news response.")
        if not batch:
            break
        if paginate and {str(item.get("id")) for item in batch} <= {str(item.get("id")) for item in payload}:
            raise VendorUnavailableError("Benzinga repeated a news page; pagination is incomplete.")
        payload.extend(batch)
    else:
        if paginate:
            raise VendorUnavailableError("Benzinga news exceeded the pagination safety limit.")

    cache.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache.with_suffix(f".{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(cache)
    return tuple(payload)


def _timestamp(value) -> datetime | None:
    if not value:
        return None
    try:
        return to_utc(parsedate_to_datetime(str(value)))
    except (TypeError, ValueError, IndexError):
        try:
            return to_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
        except ValueError:
            return None


def _collect_news(ticker: str, start_date: str, end_date: str, limit: int) -> list[dict]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        return []

    snapshot_dir = get_config().get('benzinga_snapshot_dir')
    if snapshot_dir:
        root = Path(snapshot_dir)
        manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
        if start_date < manifest['start_date'] or end_date > manifest['end_date']:
            raise VendorUnavailableError('Requested news window exceeds the frozen Benzinga snapshot.')
        name = f"{ticker or 'GLOBAL'}.json"
        data = (root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest['files'][name]['sha256']:
            raise VendorUnavailableError('Frozen Benzinga snapshot checksum mismatch.')
        articles = json.loads(data)
        start_dt, end_dt = datetime.fromisoformat(start_date), datetime.fromisoformat(end_date)
        selected = [a for a in articles if in_window(_timestamp(a.get('created')), start_dt, end_dt)][:limit]
        access_log = get_config().get('news_snapshot_access_log')
        if access_log:
            record = {'ticker':ticker or 'GLOBAL','start_date':start_date,'end_date':end_date,
                      'snapshot_sha256':manifest['files'][name]['sha256'],
                      'article_ids':[a['id'] for a in selected]}
            with _ACCESS_LOCK, Path(access_log).open('a',encoding='utf-8') as stream:
                stream.write(json.dumps(record) + '\n')
        return selected

    articles = []
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)
    cutoff = to_utc(end_dt) + timedelta(days=1)
    current = start
    while current <= end:
        current_text = current.isoformat()
        daily = _fetch_daily_news(ticker, current_text, max(1, min(limit, 100)))
        if ticker and not daily:
            # Some keys return an empty ticker-filtered feed even though the
            # same day's global pages contain articles explicitly tagged with it.
            daily = tuple(
                article for article in _fetch_daily_news("", current_text, 100, paginate=True)
                if ticker in {str(stock.get("name") or "").upper() for stock in article.get("stocks") or []}
            )
        for article in daily:
            published = _timestamp(article.get("created"))
            updated = _timestamp(article.get("updated"))
            if in_window(published, start_dt, end_dt) and (updated is None or updated < cutoff):
                articles.append(article)
        current += timedelta(days=1)

    unique = {}
    for article in articles:
        identity = article.get("id") or article.get("url")
        if identity:
            unique.setdefault(str(identity), article)
    return sorted(unique.values(), key=lambda item: _timestamp(item.get("created")) or to_utc(start_dt), reverse=True)[:limit]


def _format_articles(articles: list[dict], empty_message: str) -> str:
    if not articles:
        return empty_message

    sections = []
    for article in articles:
        title = article.get("title") or "Untitled"
        section = [f"### {title}"]
        if article.get("created"):
            section.append(f"Published: {article['created']}")
        body = article.get("teaser") or article.get("body") or ""
        if body:
            section.append(unescape(re.sub(r"<[^>]+>", " ", str(body)))[:1600])
        if article.get("url"):
            section.append(f"Link: {article['url']}")
        sections.append("\n".join(section))
    return "Source: Benzinga historical news (including ticker-tag filtering of global pages when needed).\n\n" + "\n\n".join(sections)


def get_news(ticker: str, start_date: str, end_date: str) -> str:
    """Return point-in-time company news for the requested date window."""
    limit = max(1, int(get_config()["news_article_limit"]))
    articles = _collect_news(ticker.upper().strip(), start_date, end_date, limit)
    return _format_articles(articles, f"No Benzinga company news found for {ticker} in this window.")


def get_global_news(
    as_of_date: str,
    look_back_days: int | None = None,
    limit: int | None = None,
) -> str:
    """Return point-in-time global news ending on ``as_of_date``."""
    config = get_config()
    if look_back_days is None:
        look_back_days = config["global_news_lookback_days"]
    if limit is None:
        limit = config["global_news_article_limit"]
    limit = max(1, int(limit))
    end = date.fromisoformat(as_of_date)
    start = end - timedelta(days=max(0, int(look_back_days)))
    articles = _collect_news("", start.isoformat(), end.isoformat(), limit)
    return _format_articles(articles, "No Benzinga global news found in this window.")
