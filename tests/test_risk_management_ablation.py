from unittest.mock import patch

from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.graph.setup import GraphSetup


def _node(_state):
    return {}


def _portfolio_manager(_llm, risk_management_enabled=True):
    return _node


def _workflow(risk_management_enabled):
    patches = {
        "create_sentiment_analyst": _node,
        "create_bull_researcher": _node,
        "create_bear_researcher": _node,
        "create_research_manager": _node,
        "create_trader": _node,
        "create_aggressive_debator": _node,
        "create_neutral_debator": _node,
        "create_conservative_debator": _node,
        "create_portfolio_manager": _portfolio_manager,
    }
    with patch.multiple("tradingagents.graph.setup", **patches):
        setup = GraphSetup(object(), object(), ConditionalLogic(), max_tool_rounds=1)
        return setup.setup_graph(
            selected_analysts=("social",),
            risk_management_enabled=risk_management_enabled,
        ).compile().get_graph()


def test_default_graph_routes_trader_through_risk_team():
    graph = _workflow(True)
    edges = {(edge.source, edge.target) for edge in graph.edges}

    assert ("Trader", "Aggressive Analyst") in edges
    assert "Aggressive Analyst" in graph.nodes
    assert "Conservative Analyst" in graph.nodes
    assert "Neutral Analyst" in graph.nodes
    assert ("Trader", "Portfolio Manager") not in edges


def test_ablation_bypasses_risk_team_and_keeps_portfolio_manager():
    graph = _workflow(False)
    edges = {(edge.source, edge.target) for edge in graph.edges}

    assert ("Trader", "Portfolio Manager") in edges
    assert not ({"Aggressive Analyst", "Conservative Analyst", "Neutral Analyst"} & graph.nodes.keys())
