import stat
import textwrap

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from core.codex_llm import CodexChatModel, is_codex_available
from core.llm import get_llm


def _fake_codex(tmp_path, body: str) -> str:
    script = tmp_path / "codex"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "from pathlib import Path\n"
        + textwrap.dedent(body),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return str(script)


def test_codex_chat_model_invokes_codex_exec_with_read_only_ephemeral(tmp_path, monkeypatch):
    calls_path = tmp_path / "calls.txt"
    fake = _fake_codex(
        tmp_path,
        f"""
        args = sys.argv[1:]
        Path({str(calls_path)!r}).write_text("\\n".join(args), encoding="utf-8")
        output_path = args[args.index("--output-last-message") + 1]
        stdin_text = sys.stdin.read()
        assert "system guidance" in stdin_text
        assert "generate factor idea" in stdin_text
        Path(output_path).write_text("codex response", encoding="utf-8")
        """,
    )
    monkeypatch.setenv("AIMINER_CODEX_CMD", fake)

    llm = CodexChatModel(
        model_name="gpt-5.4-test",
        cwd=str(tmp_path),
        timeout_seconds=5,
        reasoning_effort="xhigh",
    )
    response = llm.invoke(
        [
            SystemMessage(content="system guidance"),
            HumanMessage(content="generate factor idea"),
        ]
    )

    args = calls_path.read_text(encoding="utf-8").splitlines()
    assert response.content == "codex response"
    assert args[:1] == ["exec"]
    assert "--ephemeral" in args
    assert "-c" in args
    assert 'model_reasoning_effort="xhigh"' in args
    assert "--sandbox" in args
    assert "read-only" in args
    assert "--output-last-message" in args
    assert "-m" in args
    assert "gpt-5.4-test" in args
    assert "-C" in args
    assert str(tmp_path) in args


def test_codex_chat_model_applies_stop_strings(tmp_path, monkeypatch):
    fake = _fake_codex(
        tmp_path,
        """
        args = sys.argv[1:]
        output_path = args[args.index("--output-last-message") + 1]
        Path(output_path).write_text("alpha STOP beta", encoding="utf-8")
        """,
    )
    monkeypatch.setenv("AIMINER_CODEX_CMD", fake)

    llm = CodexChatModel(cwd=str(tmp_path), timeout_seconds=5)
    response = llm.invoke("hello", stop=["STOP"])

    assert response.content == "alpha "


def test_codex_chat_model_reads_reasoning_effort_from_env(tmp_path, monkeypatch):
    fake = _fake_codex(
        tmp_path,
        """
        args = sys.argv[1:]
        output_path = args[args.index("--output-last-message") + 1]
        Path(output_path).write_text("ok", encoding="utf-8")
        """,
    )
    monkeypatch.setenv("AIMINER_CODEX_CMD", fake)
    monkeypatch.setenv("AIMINER_CODEX_REASONING_EFFORT", "HIGH")

    llm = CodexChatModel(cwd=str(tmp_path), timeout_seconds=5)

    assert llm.reasoning_effort == "high"


def test_codex_chat_model_rejects_invalid_reasoning_effort():
    with pytest.raises(ValueError, match="reasoning effort"):
        CodexChatModel(reasoning_effort="extreme")


def test_codex_chat_model_falls_back_to_stdout(tmp_path, monkeypatch):
    fake = _fake_codex(
        tmp_path,
        """
        print("stdout fallback")
        """,
    )
    monkeypatch.setenv("AIMINER_CODEX_CMD", fake)

    llm = CodexChatModel(cwd=str(tmp_path), timeout_seconds=5)
    response = llm.invoke("hello")

    assert response.content == "stdout fallback"


def test_codex_chat_model_reports_nonzero_exit(tmp_path, monkeypatch):
    fake = _fake_codex(
        tmp_path,
        """
        print("boom", file=sys.stderr)
        raise SystemExit(7)
        """,
    )
    monkeypatch.setenv("AIMINER_CODEX_CMD", fake)

    llm = CodexChatModel(cwd=str(tmp_path), timeout_seconds=5)

    with pytest.raises(RuntimeError, match="exit code 7"):
        llm.invoke("hello")


def test_codex_provider_requires_cli(monkeypatch):
    monkeypatch.delenv("AIMINER_CODEX_CMD", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)

    assert not is_codex_available()
    with pytest.raises(ValueError):
        get_llm(provider="codex")


def test_get_llm_returns_codex_chat_model(tmp_path, monkeypatch):
    fake = _fake_codex(
        tmp_path,
        """
        args = sys.argv[1:]
        output_path = args[args.index("--output-last-message") + 1]
        Path(output_path).write_text("ok", encoding="utf-8")
        """,
    )
    monkeypatch.setenv("AIMINER_CODEX_CMD", fake)

    llm = get_llm(provider="codex", model_name="gpt-5.4-test", base_url="http://ignored")

    assert isinstance(llm, CodexChatModel)
    assert llm.model_name == "gpt-5.4-test"


def test_get_llm_passes_codex_reasoning_effort(tmp_path, monkeypatch):
    fake = _fake_codex(
        tmp_path,
        """
        args = sys.argv[1:]
        output_path = args[args.index("--output-last-message") + 1]
        Path(output_path).write_text("ok", encoding="utf-8")
        """,
    )
    monkeypatch.setenv("AIMINER_CODEX_CMD", fake)

    llm = get_llm(provider="codex", reasoning_effort="low")

    assert isinstance(llm, CodexChatModel)
    assert llm.reasoning_effort == "low"
