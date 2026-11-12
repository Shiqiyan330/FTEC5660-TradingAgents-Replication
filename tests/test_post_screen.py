import json

import pytest

from tradingagents.agents import post_screen


class _FakeLuna:
    model_name = "gpt-6-luna"

    def __init__(self, judgments):
        self.judgments = judgments
        self.requests = []

    def with_structured_output(self, schema):
        assert schema is post_screen.LunaJudgment
        return self

    def invoke(self, messages):
        request = json.loads(messages[1][1])
        self.requests.append(request)
        return self.judgments[request["state"]["post"]]


def _judgment(about=0.95, stance="bullish", probabilities=None):
    return {
        "about_probability": about,
        "stance": stance,
        "stance_probabilities": probabilities or {"bullish": 0.8, "bearish": 0.1, "neutral": 0.1},
    }


@pytest.mark.unit
def test_adapter_uses_jev_typed_request_and_answer_contract():
    llm = _FakeLuna({"NVDA to 200": _judgment()})

    answer = post_screen.luna_system_one(
        llm,
        {"instrument": "NVIDIA Corporation (NVDA)", "post": "NVDA to 200"},
    )

    request = llm.requests[0]
    assert request["model"] == "gpt-6-luna"
    assert set(request) == {"model", "state", "questions"}
    assert request["questions"] == post_screen.QUESTIONS
    assert answer == {
        "about": {"type": "noul", "noul": 0.95},
        "stance": {
            "type": "choice",
            "choice": "bullish",
            "confidence": 0.8,
            "probabilities": {"bullish": 0.8, "bearish": 0.1, "neutral": 0.1},
        },
    }


@pytest.mark.unit
def test_invalid_probability_distribution_fails_closed():
    llm = _FakeLuna({
        "NVDA?": _judgment(probabilities={"bullish": 0.8, "bearish": 0.1, "neutral": 0.5})
    })

    with pytest.raises(post_screen.ScreeningError, match="invalid stance probabilities"):
        post_screen.luna_system_one(llm, {"instrument": "NVDA", "post": "NVDA?"})


@pytest.mark.unit
def test_screen_drops_off_topic_posts_and_counts_uncertain_stances(monkeypatch):
    monkeypatch.setattr(post_screen, "resolve_instrument_identity", lambda ticker: {
        "company_name": "NVIDIA Corporation"
    })
    judgments = {
        "long NVDA": _judgment(),
        "NVDA puts": _judgment(stance="bearish", probabilities={"bullish": 0.1, "bearish": 0.8, "neutral": 0.1}),
        "maybe NVDA": _judgment(0.4, stance="neutral", probabilities={"bullish": 0.3, "bearish": 0.3, "neutral": 0.4}),
        "NVDA?": _judgment(probabilities={"bullish": 0.4, "bearish": 0.35, "neutral": 0.25}),
        "$AAPL $MSFT $NVDA pump": _judgment(0.1),
    }

    keep, note = post_screen.luna_screen("NVDA", _FakeLuna(judgments))(list(judgments))

    assert keep == [True, True, True, True, False]
    assert note == (
        "Screened by gpt-6-luna: 4 of the 5 posts fetched are about NVIDIA Corporation (NVDA); "
        "their stance on its stock: 1 bullish, 1 bearish, 0 neutral, 2 unclear."
    )


@pytest.mark.unit
def test_screening_is_not_gated_by_a_typesafe_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert post_screen.luna_screen("AAPL", _FakeLuna({})) is not None


@pytest.mark.unit
def test_model_failure_keeps_posts_unscreened(monkeypatch, caplog):
    class _FailedLuna(_FakeLuna):
        def invoke(self, messages):
            raise RuntimeError("offline")

    keep, note = post_screen.luna_screen("AAPL", _FailedLuna({}))(["AAPL? "])

    assert keep == [True]
    assert "Luna screening unavailable" in note
    assert "offline" not in note


@pytest.mark.unit
def test_sentiment_analyst_passes_its_luna_client_to_both_social_fetchers(monkeypatch):
    from langchain_core.messages import AIMessage

    from tradingagents.agents.analysts import sentiment_analyst

    screen = object()
    seen = []
    monkeypatch.setattr(sentiment_analyst, "luna_screen", lambda ticker, llm: screen)
    monkeypatch.setattr(sentiment_analyst.get_news, "func", lambda *args: "news")
    for name in ("fetch_stocktwits_messages", "fetch_reddit_posts"):
        monkeypatch.setattr(
            sentiment_analyst,
            name,
            lambda *args, screen=None, **kwargs: seen.append(screen) or "social",
        )

    class _LLM:
        def with_structured_output(self, *args, **kwargs):
            raise NotImplementedError

        def invoke(self, messages):
            return AIMessage(content="report")

    node = sentiment_analyst.create_sentiment_analyst(_LLM())
    node({"company_of_interest": "NVDA", "trade_date": "2026-01-09", "messages": []})

    assert seen == [screen, screen]
