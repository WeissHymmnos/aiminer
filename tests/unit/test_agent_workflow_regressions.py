from types import SimpleNamespace

from langchain_core.runnables import RunnableLambda

from agents.eval_agent import EvalAgent
from app_workflow.graph import _merge_strategy_update_into_best_snapshot, route_after_strategy
from sub_agent import _factor_result_view


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
