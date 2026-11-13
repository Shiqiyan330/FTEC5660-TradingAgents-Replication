from unittest import mock

import pytest

from tradingagents.dataflows.config import set_config
from tradingagents.dataflows.errors import VendorUnavailableError
from tradingagents.dataflows.vendors.benzinga import news


@pytest.fixture(autouse=True)
def clear_news_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("BENZINGA_API_KEY", "test-key")
    set_config({"data_cache_dir": str(tmp_path / "cache"), 'benzinga_snapshot_dir': None})


def _response(payload, status_code=200):
    response = mock.Mock(status_code=status_code)
    response.json.return_value = payload
    return response


def test_company_news_queries_each_day_and_stays_within_window(monkeypatch):
    calls = []

    def get(_url, *, params, **_kwargs):
        calls.append(params.copy())
        day = params["date"]
        return _response([
            {"id": day, "created": f"{day}T15:00:00Z", "title": f"News {day}", "url": f"https://example.test/{day}"},
            {"id": "future", "created": "2024-03-30T15:00:00Z", "title": "Future news"},
            {"id": "undated", "title": "Undated news"},
            {"id": "revised", "created": f"{day}T15:00:00Z", "updated": "2024-03-30T15:00:00Z", "title": "Later revision"},
        ])

    monkeypatch.setattr(news.requests, "get", get)
    set_config({"news_article_limit": 10})

    report = news.get_news("aapl", "2024-03-27", "2024-03-28")

    assert [call["date"] for call in calls] == ["2024-03-27", "2024-03-28"]
    assert all(call["tickers"] == "AAPL" for call in calls)
    assert all(call["token"] == "test-key" for call in calls)
    assert "News 2024-03-27" in report and "News 2024-03-28" in report
    assert "Future news" not in report
    assert "Undated news" not in report and "Later revision" not in report


def test_global_news_uses_configured_window_and_is_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(
        news.requests,
        "get",
        lambda _url, *, params, **_kwargs: calls.append(params.copy()) or _response([]),
    )
    set_config({"global_news_lookback_days": 2, "global_news_article_limit": 4})

    report = news.get_global_news("2024-03-28")
    again = news.get_global_news("2024-03-28")

    assert [call["date"] for call in calls] == ["2024-03-26", "2024-03-27", "2024-03-28"]
    assert all("tickers" not in call for call in calls)
    assert "No Benzinga global news" in report
    assert again == report


def test_real_benzinga_rfc_timestamps_are_normalized_to_utc(monkeypatch):
    monkeypatch.setattr(news.requests, "get", lambda *_args, **_kwargs: _response([
        {"id": "in", "created": "Thu, 28 Mar 2024 02:08:27 -0400", "title": "Available news"},
        {"id": "after", "created": "Thu, 28 Mar 2024 23:08:27 -0400", "title": "After UTC cutoff"},
    ]))

    report = news.get_news("AAPL", "2024-03-28", "2024-03-28")

    assert "Available news" in report
    assert "After UTC cutoff" not in report


def test_empty_ticker_query_uses_only_matching_tags_from_paginated_global_feed(monkeypatch):
    calls = []

    def get(_url, *, params, **_kwargs):
        calls.append(params.copy())
        if params.get("tickers") or params["page"] > 1:
            return _response([])
        page = params["page"]
        return _response([
            {"id": f"match{page}", "created": "Thu, 28 Mar 2024 02:08:27 -0400", "title": f"Amazon news {page}", "stocks": [{"name": "AMZN"}]},
            {"id": f"other{page}", "created": "Thu, 28 Mar 2024 02:08:27 -0400", "title": "Other company", "stocks": [{"name": "AAPL"}]},
        ])

    monkeypatch.setattr(news.requests, "get", get)
    report = news.get_news("AMZN", "2024-03-28", "2024-03-28")

    assert "Amazon news 0" in report and "Amazon news 1" in report
    assert "Other company" not in report
    assert [call["page"] for call in calls] == [0, 0, 1, 2]


def test_http_error_is_sanitized(monkeypatch):
    monkeypatch.setattr(news.requests, "get", lambda *_args, **_kwargs: _response({}, 403))

    with pytest.raises(VendorUnavailableError) as caught:
        news.get_news("AAPL", "2024-03-28", "2024-03-28")

    assert "HTTP 403" in str(caught.value)
    assert "test-key" not in str(caught.value)


def test_frozen_snapshot_is_offline_and_rejects_outside_window(monkeypatch, tmp_path):
    import hashlib
    import json
    root = tmp_path / 'snapshot'
    root.mkdir()
    (root / 'AAPL.json').write_text(json.dumps([
        {'created':'2024-03-27T12:00:00Z','title':'Earlier'},
        {'created':'2024-03-28T12:00:00Z','title':'Current'},
    ]))
    sha = hashlib.sha256((root / 'AAPL.json').read_bytes()).hexdigest()
    (root / 'manifest.json').write_text(json.dumps({'start_date':'2024-03-21','end_date':'2024-03-28',
                                                  'files':{'AAPL.json':{'sha256':sha}}}))
    set_config({'benzinga_snapshot_dir':str(root)})
    monkeypatch.setattr(news.requests,'get',lambda *a, **k: pytest.fail('snapshot accessed the network'))
    assert 'Current' in news.get_news('AAPL','2024-03-28','2024-03-28')
    assert 'Earlier' not in news.get_news('AAPL','2024-03-28','2024-03-28')
    with pytest.raises(VendorUnavailableError):
        news.get_news('AAPL','2024-03-01','2024-03-28')
    (root / 'AAPL.json').write_text('[]')
    with pytest.raises(VendorUnavailableError):
        news.get_news('AAPL','2024-03-28','2024-03-28')
