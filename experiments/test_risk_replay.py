import unittest
from copy import deepcopy
from unittest.mock import patch

from experiments import run_risk_replay as replay
from experiments.run_tradingagents_table1 import _entry_rows
from experiments.summarize_risk_replay import summarize
from tradingagents.memory.log import TradingMemoryLog


class RiskReplayTests(unittest.TestCase):
    def test_frozen_prefix_cannot_leak_prior_risk_decision_or_future_memory(self):
        saved = {key: {"history": "research", "count": 2} if key == "investment_debate_state"
                 else "upstream evidence" for key in replay.PREFIX_KEYS}
        saved.update(company_of_interest="AAPL", trade_date="2024-03-28",
                     risk_debate_state={"history": "LEAK", "count": 3},
                     final_trade_decision="LEAK", final_rating="Sell", past_context="FUTURE")
        state = replay.frozen_prefix(saved)
        self.assertNotIn("final_trade_decision", state)
        self.assertEqual(state["risk_debate_state"]["count"], 0)
        self.assertEqual(state["risk_debate_state"]["history"], "")
        self.assertEqual(state["past_context"], "")
        self.assertEqual(state["investment_plan"], saved["investment_plan"])
        state["investment_debate_state"]["history"] = "modified"
        self.assertEqual(saved["investment_debate_state"]["history"], "research")

    def test_replay_has_three_risk_turns_only_in_full_condition(self):
        def debator(speaker):
            def node(state):
                return {"risk_debate_state": {
                    **state["risk_debate_state"], "latest_speaker": speaker,
                    "count": state["risk_debate_state"]["count"] + 1,
                }}
            return node

        factories = {
            "create_aggressive_debator": lambda _: debator("Aggressive"),
            "create_conservative_debator": lambda _: debator("Conservative"),
            "create_neutral_debator": lambda _: debator("Neutral"),
            "create_portfolio_manager": lambda _, enabled: lambda state: {"final_rating": "Hold"},
        }
        with patch.multiple(replay, **factories):
            initial = replay.Propagator().create_initial_state("AAPL", "2024-03-28")
            full = replay.workflow(None, None, True).invoke(initial)
            no_risk = replay.workflow(None, None, False).invoke(initial)
        self.assertEqual(full["risk_debate_state"]["count"], 3)
        self.assertEqual(no_risk["risk_debate_state"]["count"], 0)
        self.assertEqual(full["final_rating"], no_risk["final_rating"])

    def test_settled_return_export_uses_memory_logs_raw_key(self):
        entry = TradingMemoryLog()._parse_entry(
            "[2024-03-28 | AAPL | Sell | -0.9% | -0.3% | 5d | resolved:2024-04-08]\n\n"
            "DECISION:\nSell\nREFLECTION:\nOutcome"
        )
        self.assertEqual(_entry_rows([entry]).iloc[0]["raw_return"], "-0.9%")

    def test_summary_rejects_mismatched_input_and_reports_trial_variance(self):
        sources, records = {}, []
        for ticker in replay.TICKERS:
            state = {key: "evidence" for key in replay.PREFIX_KEYS}
            state.update(company_of_interest=ticker, trade_date="2024-03-28")
            sources[ticker] = {"state": state, "source_state_sha256": "source"}
            for trial in range(1, 4):
                for condition in ("full", "no_risk"):
                    enabled = condition == "full"
                    records.append({"trial": trial, "ticker": ticker, "condition": condition,
                                    "risk_management_enabled": enabled,
                                    "settings": {"max_risk_discuss_rounds": 1},
                                    "input_sha256": replay.digest(replay.frozen_prefix(state)),
                                    "source_state_sha256": "source",
                                    "risk_debate_state": {"count": 3 if enabled else 0},
                                    "final_rating": "Sell" if enabled else "Underweight"})
        result = summarize(records, sources)
        self.assertEqual(result["statistics"]["delta_pp"]["mean"], 50)
        self.assertEqual(result["statistics"]["delta_pp"]["sample_variance_pp2"], 0)
        varied = deepcopy(records)
        for record in varied:
            if record["trial"] == 3 and record["condition"] == "full":
                record["final_rating"] = "Underweight"
        varied_summary = summarize(varied, sources)
        self.assertAlmostEqual(varied_summary["statistics"]["delta_pp"]["mean"], 100 / 3)
        self.assertAlmostEqual(varied_summary["statistics"]["delta_pp"]["sample_variance_pp2"], 2500 / 3)
        tampered = deepcopy(records)
        tampered[0]["input_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "common-input mismatch"):
            summarize(tampered, sources)
        with self.assertRaisesRegex(ValueError, "missing"):
            summarize(records[:-1], sources)


if __name__ == "__main__":
    unittest.main()
