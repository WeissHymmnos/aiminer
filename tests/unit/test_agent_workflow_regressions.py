from types import SimpleNamespace

from langchain_core.runnables import RunnableLambda

from agents.eval_agent import EvalAgent
from app_workflow.graph import (
    _merge_strategy_update_into_best_snapshot,
    _state_has_evaluation_failure,
    route_after_factor,
    route_after_strategy,
)
from core.agent_result import state_to_agent_result
from core.alphaeval.local_eval import LocalDataEval
from core.hybrid_knowledge import HybridKnowledge
from sub_agent import AlphaResearcher, _factor_result_view


class _KnowledgeStub:
    def __init__(self):
        self.rag = SimpleNamespace(add_experience=lambda **_: None)


def _agent_without_init() -> EvalAgent:
    agent = EvalAgent.__new__(EvalAgent)
    agent.knowledge = _KnowledgeStub()
    agent.llm = RunnableLambda(
        lambda _: SimpleNamespace(
            content=(
                '{"review_summary":"inverse signal is tradable",'
                '"is_effective":true,'
                '"suggested_improvements":"keep sign metadata"}'
            )
        )
    )
    return agent


def test_main_backtest_metrics_survive_robustness_failure(monkeypatch):
    class DummyEvaluator:
        def run(self):
            self.ic = -0.042
            self.oos_ic = -0.039
            self.rankic = -0.031
            self.rre = 0.0
            self.sharpe = 1.25
            self.max_dd = -0.08
            self.plot_paths = {"equity": "results/reports/equity.png"}
            self.daily_returns = {"2024-01-02": 0.01}

        def run_robustness_test(self):
            raise RuntimeError("noise backend unavailable")

    import core.evaluator_factory as evaluator_factory

    monkeypatch.setattr(
        evaluator_factory, "build_evaluator", lambda **_: DummyEvaluator()
    )
    agent = _agent_without_init()
    agent._state_data_backend = "local"
    agent._state_market_mode = "single"
    agent._state_market_profile = "cn_stock"
    agent._state_market_profiles = ["cn_stock"]
    agent._state_local_data_path = "/tmp/local-data"
    agent._state_local_data_layout = "auto"

    result = agent._execute_alphaeval_backtest(
        "Rank($close)", mode="qlib", engine="pandas"
    )

    assert result.get("_simulated") is not True
    assert result["information_coefficient"] == -0.042
    assert result["plot_paths"] == {"equity": "results/reports/equity.png"}
    assert result["daily_returns"] == {"2024-01-02": 0.01}
    assert result["robustness_error"] == "noise backend unavailable"
    assert result["ic_direction"] == -1
    assert result["ic_direction_label"] == "negative"
    assert result["ic_abs"] == 0.042


def test_eval_backtest_failure_returns_failed_metrics_not_simulated(monkeypatch):
    import core.evaluator_factory as evaluator_factory

    def _raise_runtime_error(**_kwargs):
        raise RuntimeError("factor runtime failure")

    monkeypatch.setattr(evaluator_factory, "build_evaluator", _raise_runtime_error)
    agent = _agent_without_init()
    agent._state_data_backend = "local"
    agent._state_market_mode = "single"
    agent._state_market_profile = "cn_stock"
    agent._state_market_profiles = ["cn_stock"]
    agent._state_local_data_path = "/tmp/local-data"
    agent._state_local_data_layout = "auto"

    result = agent._execute_alphaeval_backtest(
        "Sqrt(Div(20,19))", mode="ricequant", engine="pandas"
    )

    assert result.get("_simulated") is not True
    assert result["_evaluation_failed"] is True
    assert result["information_coefficient"] == 0.0
    assert result["rank_ic"] == 0.0
    assert "factor runtime failure" in result["evaluation_error"]


def test_eval_agent_skips_backend_for_invalid_factor_syntax():
    agent = _agent_without_init()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("invalid syntax must not reach the evaluator backend")

    agent._execute_alphaeval_backtest = fail_if_called

    result = agent(
        {
            "iteration": 1,
            "hypothesis_name": "Bad Parentheses",
            "hypothesis_description": "Generated expression has mismatched parentheses.",
            "code_expression": "Sub(Mul(1, $close)",
            "is_valid_syntax": False,
            "syntax_error": "parentheses are not balanced",
            "evaluation_mode": "ricequant",
            "evaluation_engine": "pandas",
            "data_backend": "local",
            "market_profile": "cn_futures",
            "market_profiles": ["cn_futures"],
            "best_ic": -999.0,
            "best_ic_abs": -1.0,
            "patience_counter": 0,
        }
    )

    assert result["evaluation_failed"] is True
    assert result["backtest_metrics"]["information_coefficient"] == 0.0
    assert result["backtest_metrics"]["rank_ic"] == 0.0
    assert "parentheses are not balanced" in result["evaluation_error"]
    assert result["patience_counter"] == 1


def test_invalid_factor_still_routes_through_eval_for_failed_metrics():
    assert route_after_factor(
        {"code_expression": "Sub(Mul(1, $close)", "is_valid_syntax": False}
    ) == "eval_agent"


def test_evaluation_failure_is_detected_from_state_or_metrics():
    assert _state_has_evaluation_failure({"evaluation_failed": True}) is True
    assert (
        _state_has_evaluation_failure(
            {"backtest_metrics": {"_evaluation_failed": True}}
        )
        is True
    )
    assert _state_has_evaluation_failure({"backtest_metrics": {}}) is False


def test_hybrid_knowledge_skips_wiki_update_for_evaluation_failure():
    class FailingWiki:
        def add_or_update_page(self, **_kwargs):
            raise AssertionError("failed evaluations must not update wiki")

    knowledge = HybridKnowledge.__new__(HybridKnowledge)
    knowledge.wiki = FailingWiki()

    result = knowledge.update_wiki_after_eval(
        {
            "evaluation_failed": True,
            "hypothesis_name": "Bad Syntax Factor",
            "backtest_metrics": {
                "information_coefficient": 0.0,
                "rank_ic": 0.0,
                "evaluation_error": "invalid expression",
            },
        }
    )

    assert result == {}


def test_local_data_eval_robustness_does_not_use_ricequant_network(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("RiceQuant robustness path should not run for local data")

    import core.alphaeval.rq_eval as rq_eval

    monkeypatch.setattr(rq_eval.RiceQuantEval, "run", fail_if_called)
    evaluator = LocalDataEval.__new__(LocalDataEval)
    evaluator.ic = 0.01

    evaluator.run_robustness_test()

    assert evaluator.rre is None


def test_eval_agent_tracks_negative_ic_best_snapshot_by_abs_strength():
    agent = _agent_without_init()
    agent._execute_alphaeval_backtest = lambda *_, **__: {
        "information_coefficient": -0.06,
        "rank_ic": -0.05,
        "rre": 0.1,
        "sharpe": 0.8,
        "max_drawdown": -0.03,
        "daily_returns": {"2024-01-02": 0.02},
        "plot_paths": {"layers": "results/reports/layers.png"},
    }

    result = agent(
        {
            "iteration": 2,
            "role_prompt": "inverse alpha researcher",
            "hypothesis_name": "Inverse Momentum",
            "hypothesis_description": "High signal predicts lower forward returns.",
            "rationale": "Mean reversion after crowding.",
            "math_formula": "-momentum",
            "variables_defined": {"momentum": "close change"},
            "code_expression": "Rank(Delta($close, 5))",
            "evaluation_mode": "qlib",
            "evaluation_engine": "pandas",
            "data_backend": "qlib",
            "market_profile": "cn_stock",
            "market_profiles": ["cn_stock"],
            "best_ic": 0.02,
            "best_ic_abs": 0.02,
            "best_code_expression": "WeakPositive($close)",
            "patience_counter": 1,
        }
    )

    assert result["best_ic"] == -0.06
    assert result["best_ic_abs"] == 0.06
    assert result["best_code_expression"] == "Rank(Delta($close, 5))"
    assert result["patience_counter"] == 0
    snapshot = result["best_factor_snapshot"]
    assert snapshot["code"] == "Rank(Delta($close, 5))"
    assert snapshot["metrics"]["ic_direction"] == -1
    assert snapshot["plot_paths"] == {"layers": "results/reports/layers.png"}


def test_eval_agent_falls_back_when_review_llm_returns_empty():
    agent = EvalAgent.__new__(EvalAgent)
    agent.knowledge = _KnowledgeStub()
    agent.llm = RunnableLambda(lambda _: SimpleNamespace(content=""))
    agent._execute_alphaeval_backtest = lambda *_, **__: {
        "information_coefficient": 0.031,
        "rank_ic": 0.027,
        "sharpe": 0.4,
        "max_drawdown": -0.12,
    }

    result = agent(
        {
            "iteration": 1,
            "hypothesis_name": "Fallback Review",
            "hypothesis_description": "Review LLM may be empty.",
            "code_expression": "Rank($close)",
            "evaluation_mode": "qlib",
            "evaluation_engine": "pandas",
            "data_backend": "qlib",
            "market_profile": "cn_stock",
            "market_profiles": ["cn_stock"],
            "best_ic": -999.0,
            "best_ic_abs": -1.0,
            "patience_counter": 0,
        }
    )

    assert "error" not in result
    assert result["is_effective"] is True
    assert "LLM review unavailable" in result["review_summary"]
    assert result["best_ic"] == 0.031
    assert result["patience_counter"] == 0


def test_sub_agent_result_uses_best_snapshot_and_plot_paths():
    final_state = {
        "iteration": 3,
        "hypothesis_name": "Last weaker factor",
        "code_expression": "Last($close)",
        "backtest_metrics": {"information_coefficient": 0.01},
        "daily_returns": {"2024-01-03": 0.003},
        "plot_paths": {"equity": "last.png"},
        "best_factor_snapshot": {
            "iteration": 1,
            "hypothesis": "Best complete factor",
            "code": "Best($close)",
            "metrics": {"information_coefficient": 0.04},
            "returns": {"2024-01-02": 0.02},
            "plot_paths": {"equity": "best.png"},
            "strategy_failure_reason": "panel_construction_failed",
        },
    }

    view = _factor_result_view(final_state)

    assert view["iteration"] == 1
    assert view["hypothesis"] == "Best complete factor"
    assert view["code"] == "Best($close)"
    assert view["metrics"] == {"information_coefficient": 0.04}
    assert view["returns"] == {"2024-01-02": 0.02}
    assert view["plot_paths"] == {"equity": "best.png"}
    assert view["strategy_failure_reason"] == "panel_construction_failed"


def test_agent_result_accepts_best_snapshot_despite_later_error():
    result = state_to_agent_result(
        {
            "run_id": "run_1",
            "agent_id": "agent_1",
            "role_prompt": "波动率专家",
            "error": "Connection error.",
            "best_factor_snapshot": {
                "iteration": 6,
                "hypothesis": "Recovered alpha",
                "code": "Rank($close)",
                "metrics": {"information_coefficient": 0.0278, "rank_ic": 0.0257},
                "returns": {"2024-01-01": 0.01},
                "is_simulated": False,
            },
        }
    )

    assert result["error"] is None
    assert result["terminal_error"] == "Connection error."
    assert result["hypothesis"] == "Recovered alpha"
    assert result["perf_metric"] == 0.0278


def test_sub_agent_checkpoint_hydrates_resume_state():
    agent = AlphaResearcher.__new__(AlphaResearcher)
    agent.max_iterations = 300
    agent.role_prompt = "动量专家"

    state = agent._checkpoint_to_initial_state(
        {
            "iteration": 56,
            "hypothesis": "Recovered alpha",
            "code": "Rank($close)",
            "metrics": {"information_coefficient": -0.031, "rank_ic": -0.02},
            "returns": {"2024-01-02": 0.01},
            "selection_score": 1.2,
            "is_simulated": False,
        }
    )

    assert state["iteration"] == 57
    assert state["best_ic"] == -0.031
    assert state["best_ic_abs"] == 0.031
    assert state["best_code_expression"] == "Rank($close)"
    snapshot = state["best_factor_snapshot"]
    assert snapshot["iteration"] == 56
    assert snapshot["hypothesis"] == "Recovered alpha"
    assert snapshot["metrics"]["rank_ic"] == -0.02
    assert snapshot["selection_score"] == 1.2


def test_strategy_stage_failure_is_nonfatal_and_keeps_best_factor_snapshot():
    assert route_after_strategy({"error": "strategy agent failed"}) == "wiki_update"

    state = {
        "iteration": 1,
        "code_expression": "Best($close)",
        "strategy_candidates": [{"template_name": "candidate"}],
        "best_factor_snapshot": {
            "iteration": 1,
            "code": "Best($close)",
            "code_expression": "Best($close)",
            "metrics": {"information_coefficient": 0.03},
        },
    }
    update = _merge_strategy_update_into_best_snapshot(
        state,
        {"strategy_results": [], "strategy_failure_reason": "panel_construction_failed"},
    )

    assert "error" not in update
    assert update["strategy_failure_reason"] == "panel_construction_failed"
    assert update["best_factor_snapshot"]["code"] == "Best($close)"
    assert (
        update["best_factor_snapshot"]["strategy_failure_reason"]
        == "panel_construction_failed"
    )
