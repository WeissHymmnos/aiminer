from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def test_aiminer_package_is_importable():
    import aiminer

    assert hasattr(aiminer, "__version__")
    assert aiminer.__version__ == "0.1.0"


def test_core_submodules_are_importable():
    from aiminer.core import settings
    from aiminer.core import evaluator_factory
    from aiminer.core import interfaces
    from aiminer.core import constants

    assert hasattr(settings, "AiminerSettings")
    assert hasattr(evaluator_factory, "build_evaluator")
    assert hasattr(interfaces, "BacktestBackend")
    assert hasattr(interfaces, "VectorStore")
    assert hasattr(constants, "IC_ACCEPT_THRESHOLD")


def test_agent_submodules_are_importable():
    from aiminer.agents import idea_agent
    from aiminer.agents import factor_agent
    from aiminer.agents import eval_agent
    from aiminer.agents import strategy_agent

    assert hasattr(idea_agent, "IdeaAgent")
    assert hasattr(factor_agent, "FactorAgent")
    assert hasattr(eval_agent, "EvalAgent")
    assert hasattr(strategy_agent, "StrategyAgent")


def test_workflow_submodules_are_importable():
    from aiminer.app_workflow import graph
    from aiminer.app_workflow import state

    assert hasattr(graph, "build_workflow")
    assert hasattr(state, "AlphaMinerState")


def test_schemas_are_importable():
    from aiminer.schemas import messages

    assert hasattr(messages, "HypothesisOutput")
    assert hasattr(messages, "ReflexiveReviewOutput")


def test_entry_point_modules_are_importable():
    from aiminer import manager
    from aiminer import main
    from aiminer import api
    from aiminer import tui
    from aiminer import sub_agent

    assert hasattr(manager, "main")
    assert hasattr(main, "main")
    assert hasattr(api, "main")
    assert hasattr(tui, "main")
    assert hasattr(sub_agent, "AlphaResearcher")


def test_manager_argparse_does_not_run_without_args():
    from aiminer.manager import main as manager_main

    with pytest.raises(SystemExit):
        manager_main()


def test_manager_argparse_accepts_minimal_args():
    from aiminer.manager import main as manager_main
    from aiminer.manager import PortfolioManager

    with patch.object(PortfolioManager, "run_swarm") as mock_run:
        with patch("multiprocessing.set_start_method"):
            manager_main(["--iterations", "1", "--roles", "test"])

    mock_run.assert_called_once()


def test_main_argparse_does_not_run_without_args():
    from aiminer.main import main as main_main

    with pytest.raises(SystemExit):
        main_main()


def test_main_argparse_accepts_help():
    from aiminer.main import main as main_main

    with patch.object(sys, "argv", ["aiminer", "--help"]):
        with pytest.raises(SystemExit):
            main_main()


def test_api_app_is_callable():
    from aiminer.api import app

    assert app is not None
    assert callable(app)


def test_tui_app_class_exists():
    from aiminer.tui import TUIApp

    assert TUIApp is not None


def test_sub_agent_uses_injected_settings():
    from aiminer.sub_agent import AlphaResearcher
    from aiminer.core.settings import AiminerSettings

    settings = AiminerSettings(max_iterations=2, evaluation_mode="ricequant")
    agent = AlphaResearcher(
        role_prompt="test",
        max_iterations=3,
        settings=settings,
    )
    assert agent.settings is settings
    assert agent.max_iterations == 2


def test_hybrid_knowledge_uses_injected_settings():
    from aiminer.core.hybrid_knowledge import HybridKnowledge
    from aiminer.core.settings import AiminerSettings

    settings = AiminerSettings(rebuild_rag=True, embedding_provider="local")
    with patch("aiminer.core.hybrid_knowledge.RAGModule") as mock_rag:
        with patch("aiminer.core.hybrid_knowledge.LLMWiki") as mock_wiki:
            hk = HybridKnowledge(settings=settings)

    assert hk.settings is settings
    mock_rag.assert_called_once()
    mock_wiki.assert_called_once()


def test_rag_module_uses_injected_settings():
    from aiminer.core.rag import RAGModule
    from aiminer.core.settings import AiminerSettings

    settings = AiminerSettings(data_dir="/tmp/data")
    rag = RAGModule(
        db_dir="/tmp/chroma",
        docs_dir="/tmp/docs",
        settings=settings,
    )
    assert rag.settings is settings


def test_evaluator_factory_return_annotated_with_backtest_backend():
    from aiminer.core.evaluator_factory import build_evaluator

    import inspect

    sig = inspect.signature(build_evaluator)
    assert sig.return_annotation == "BacktestBackend"


def test_pyproject_src_layout_is_configured():
    root = Path(__file__).resolve().parents[2]
    pyproject = root / "pyproject.toml"
    assert pyproject.exists()

    text = pyproject.read_text(encoding="utf-8")
    assert 'name = "aiminer"' in text
    assert '[project.scripts]' in text
    assert 'aiminer = "aiminer.main:main"' in text
    assert 'aiminer-manager = "aiminer.manager:main"' in text
    assert 'aiminer-tui = "aiminer.tui:main"' in text
    assert 'aiminer-api = "aiminer.api:main"' in text
    assert 'package-dir = {"" = "src"}' in text
