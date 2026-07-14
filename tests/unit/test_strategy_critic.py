import json
import unittest
from unittest.mock import patch, MagicMock

from aiminer.agents.strategy_critic import (
    DEFAULT_IMPROVEMENT_EPSILON,
    StrategyCritic,
    _config_signature,
    _improvement_satisfied,
)


def _llm_response(payload: dict) -> MagicMock:
    """Build the object the LangChain prompt | llm pipeline returns."""
    msg = MagicMock()
    msg.content = json.dumps(payload)
    return msg


def _build_critic(payload: dict) -> StrategyCritic:
    """Construct a critic with the LLM stubbed to return `payload`."""
    with patch("aiminer.agents.strategy_critic.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _llm_response(payload)
        # The critic builds `prompt | self.llm` then calls .invoke({}).
        # Replace the chained pipeline with a stub that returns the canned response.
        mock_llm.__or__ = lambda self, other: self
        mock_llm.__ror__ = lambda self, other: self
        mock_get_llm.return_value = mock_llm
        critic = StrategyCritic()
    return critic


def _base_state(**overrides):
    state = {
        "agent_id": "agent_test",
        "market_profile": "cn_stock",
        "evaluation_engine": "polars",
        "market_analysis_start_date": "2017-01-01",
        "market_analysis_end_date": "2020-10-31",
        "code_expression": "rank(close)",
        "hypothesis_name": "rank_close",
        "selection_score": 1.0,
        "best_strategy_metrics": {
            "sharpe": 0.4, "annualized_return": 0.08, "max_drawdown": -0.25,
            "turnover": 0.6, "cost_drag": 0.01,
        },
        "best_strategy_result": {
            "strategy_id": "agent_test_r0_cand_1",
            "strategy_config": {
                "strategy_mode": "cross_sectional",
                "direction": "long_short",
                "selection_rule": "top_bottom_n",
                "rebalance_freq": "daily",
                "top_n": 20, "bottom_n": 20,
                "max_positions": 40,
                "max_weight_per_position": 0.05,
                "min_holding_days": 1,
                "commission_bps": 5.0,
                "slippage_bps": 5.0,
            },
            "metrics": {"sharpe": 0.4, "annualized_return": 0.08, "max_drawdown": -0.25},
            "trade_stats": {"avg_turnover": 0.6, "rebalance_days": 240},
            "period_metrics": {"yearly": {"2018": {"return": -0.05, "sharpe": -0.3}}},
        },
        "strategy_refinement_round": 0,
        "max_strategy_refinement_rounds": 2,
        "strategy_refinement_history": [],
    }
    state.update(overrides)
    return state


class TestImprovementGate(unittest.TestCase):
    def test_no_history_treated_as_improvement(self):
        self.assertTrue(_improvement_satisfied(0.5, None))

    def test_positive_score_requires_relative_lift(self):
        self.assertFalse(_improvement_satisfied(1.01, 1.0))  # +1% < 5%
        self.assertTrue(_improvement_satisfied(1.06, 1.0))   # +6% > 5%

    def test_non_positive_score_uses_absolute_lift(self):
        self.assertFalse(_improvement_satisfied(-0.01, -0.02))
        self.assertTrue(_improvement_satisfied(0.10, -0.02))


class TestConfigSignature(unittest.TestCase):
    def test_identical_configs_share_signature(self):
        a = {"strategy_mode": "cross_sectional", "top_n": 20, "min_holding_days": 1}
        b = {"strategy_mode": "cross_sectional", "top_n": 20, "min_holding_days": 1}
        self.assertEqual(_config_signature(a), _config_signature(b))

    def test_param_change_changes_signature(self):
        a = {"strategy_mode": "cross_sectional", "top_n": 20}
        b = {"strategy_mode": "cross_sectional", "top_n": 30}
        self.assertNotEqual(_config_signature(a), _config_signature(b))


class TestStrategyCritic(unittest.TestCase):
    def test_proposals_become_validated_candidates(self):
        payload = {
            "failure_modes": ["high_turnover"],
            "should_continue": True,
            "rationale": "Slow rebalancing should reduce turnover.",
            "proposals": [
                {
                    "template_name": "cs_top_bottom_weekly",
                    "strategy_mode": "cross_sectional",
                    "direction": "long_short",
                    "selection_rule": "top_bottom_n",
                    "rebalance_freq": "weekly",
                    "thresholds": {},
                    "counts": {"top_n": 30, "bottom_n": 30},
                    "holding_constraints": {
                        "max_positions": 60,
                        "max_weight_per_position": 0.04,
                        "min_holding_days": 3,
                    },
                    "cost_model": {"commission_bps": 5.0, "slippage_bps": 5.0},
                    "rationale": "Weekly rebalance to cut turnover.",
                }
            ],
        }
        critic = _build_critic(payload)
        result = critic(_base_state())

        self.assertEqual(result["strategy_refinement_round"], 1)
        self.assertEqual(len(result["strategy_candidates"]), 1)
        cand = result["strategy_candidates"][0]
        self.assertIn("strategy_config", cand)
        self.assertEqual(cand["strategy_config"]["rebalance_freq"], "weekly")
        history = result["strategy_refinement_history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["failure_modes"], ["high_turnover"])
        self.assertEqual(history[0]["proposed_count"], 1)

    def test_should_continue_false_halts_gracefully(self):
        payload = {
            "failure_modes": [],
            "should_continue": False,
            "rationale": "Metrics already strong.",
            "proposals": [],
        }
        critic = _build_critic(payload)
        result = critic(_base_state())

        self.assertNotIn("strategy_candidates", result)
        history = result["strategy_refinement_history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["halt_reason"], "critic_stop")

    def test_max_rounds_short_circuits_without_calling_llm(self):
        payload = {
            "failure_modes": ["x"], "should_continue": True,
            "rationale": "should never run", "proposals": [],
        }
        critic = _build_critic(payload)
        # Reset the stub so we can detect any unexpected call.
        critic.llm.invoke.reset_mock()

        state = _base_state(strategy_refinement_round=2, max_strategy_refinement_rounds=2)
        result = critic(state)

        critic.llm.invoke.assert_not_called()
        self.assertEqual(
            result["strategy_refinement_history"][-1]["halt_reason"], "max_rounds"
        )
        self.assertNotIn("strategy_candidates", result)

    def test_no_improvement_short_circuits_without_calling_llm(self):
        payload = {
            "failure_modes": ["x"], "should_continue": True,
            "rationale": "should never run", "proposals": [],
        }
        critic = _build_critic(payload)
        critic.llm.invoke.reset_mock()

        state = _base_state(
            selection_score=1.01,
            strategy_refinement_history=[
                {"round": 0, "selection_score": 1.0}
            ],
        )
        result = critic(state)

        critic.llm.invoke.assert_not_called()
        self.assertEqual(
            result["strategy_refinement_history"][-1]["halt_reason"], "no_improvement"
        )

    def test_duplicate_proposal_is_dropped(self):
        # Critic proposes a config identical to the current best — must be filtered.
        payload = {
            "failure_modes": ["redundant"],
            "should_continue": True,
            "rationale": "duplicate test",
            "proposals": [
                {
                    "template_name": "cs_top_bottom",
                    "strategy_mode": "cross_sectional",
                    "direction": "long_short",
                    "selection_rule": "top_bottom_n",
                    "rebalance_freq": "daily",
                    "thresholds": {},
                    "counts": {"top_n": 20, "bottom_n": 20},
                    "holding_constraints": {
                        "max_positions": 40,
                        "max_weight_per_position": 0.05,
                        "min_holding_days": 1,
                    },
                    "cost_model": {"commission_bps": 5.0, "slippage_bps": 5.0},
                    "rationale": "same as current best",
                }
            ],
        }
        critic = _build_critic(payload)
        result = critic(_base_state())

        self.assertNotIn("strategy_candidates", result)
        self.assertEqual(
            result["strategy_refinement_history"][-1]["halt_reason"], "no_novel_proposals"
        )

    def test_invalid_proposal_is_skipped_but_others_kept(self):
        payload = {
            "failure_modes": ["mixed"],
            "should_continue": True,
            "rationale": "one invalid one valid",
            "proposals": [
                {
                    # Invalid: unknown enum values should still be rejected.
                    "template_name": "broken_ts",
                    "strategy_mode": "unsupported_mode",
                    "direction": "sideways",
                    "selection_rule": "unsupported_rule",
                    "rebalance_freq": "daily",
                    "thresholds": {},
                    "counts": {"top_n": 10},
                    "holding_constraints": {"max_weight_per_position": 0.05, "min_holding_days": 1},
                    "cost_model": {"commission_bps": 5.0, "slippage_bps": 5.0},
                    "rationale": "should be skipped",
                },
                {
                    "template_name": "valid_cs",
                    "strategy_mode": "cross_sectional",
                    "direction": "long_only",
                    "selection_rule": "top_n",
                    "rebalance_freq": "weekly",
                    "thresholds": {},
                    "counts": {"top_n": 25},
                    "holding_constraints": {
                        "max_positions": 25,
                        "max_weight_per_position": 0.06,
                        "min_holding_days": 3,
                    },
                    "cost_model": {"commission_bps": 5.0, "slippage_bps": 5.0},
                    "rationale": "long-only weekly",
                },
            ],
        }
        critic = _build_critic(payload)
        result = critic(_base_state())

        self.assertEqual(len(result["strategy_candidates"]), 1)
        self.assertEqual(
            result["strategy_candidates"][0]["template_name"], "valid_cs"
        )

    def test_llm_failure_falls_back_to_halt(self):
        critic = _build_critic({"should_continue": True, "proposals": []})
        # Force LLM invocation to raise.
        critic.llm.invoke.side_effect = RuntimeError("boom")
        result = critic(_base_state())

        self.assertEqual(
            result["strategy_refinement_history"][-1]["halt_reason"], "llm_error"
        )
        self.assertNotIn("strategy_candidates", result)


if __name__ == "__main__":
    unittest.main()
