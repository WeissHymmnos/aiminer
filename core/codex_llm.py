from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field, model_validator


SUPPORTED_CODEX_REASONING_EFFORTS = ("low", "medium", "high", "xhigh")


def normalize_reasoning_effort(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text not in SUPPORTED_CODEX_REASONING_EFFORTS:
        raise ValueError(
            "Codex reasoning effort must be one of: "
            f"{', '.join(SUPPORTED_CODEX_REASONING_EFFORTS)}"
        )
    return text


def codex_reasoning_effort_from_env() -> str | None:
    return normalize_reasoning_effort(
        os.getenv("AIMINER_CODEX_REASONING_EFFORT")
        or os.getenv("AIMINER_LLM_REASONING_EFFORT")
    )


def codex_command() -> list[str] | None:
    raw = os.getenv("AIMINER_CODEX_CMD", "codex").strip()
    if not raw:
        return None
    parts = shlex.split(raw)
    if not parts:
        return None
    executable = parts[0]
    if Path(executable).is_absolute():
        if not Path(executable).exists():
            return None
    elif shutil.which(executable) is None:
        return None
    return parts


def is_codex_available() -> bool:
    return codex_command() is not None


class CodexChatModel(BaseChatModel):
    """LangChain chat wrapper around local `codex exec`.

    The wrapper intentionally uses a read-only, ephemeral Codex session so it
    behaves as an LLM provider rather than a code-mutating agent.
    """

    model_name: str = "gpt-5.4"
    temperature: float = 0.7
    timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("AIMINER_CODEX_TIMEOUT_SECONDS", "180"))
    )
    reasoning_effort: str | None = Field(default_factory=codex_reasoning_effort_from_env)
    cwd: str = Field(default_factory=os.getcwd)
    sandbox: str = "read-only"

    @property
    def _llm_type(self) -> str:
        return "codex"

    @model_validator(mode="after")
    def _validate_reasoning_effort(self) -> "CodexChatModel":
        self.reasoning_effort = normalize_reasoning_effort(self.reasoning_effort)
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        command = codex_command()
        if command is None:
            raise RuntimeError(
                "Codex CLI is not available. Install `codex` or set AIMINER_CODEX_CMD."
            )

        prompt = self._messages_to_prompt(messages)
        with tempfile.TemporaryDirectory(prefix="aiminer-codex-") as tmp_dir:
            output_path = Path(tmp_dir) / "last_message.txt"
            argv = [*command, "exec"]
            if self.reasoning_effort:
                argv.extend(["-c", f'model_reasoning_effort="{self.reasoning_effort}"'])
            argv.extend(
                [
                    "--ephemeral",
                    "--sandbox",
                    self.sandbox,
                    "--color",
                    "never",
                    "--output-last-message",
                    str(output_path),
                    "-m",
                    self.model_name,
                    "-C",
                    self.cwd,
                    "-",
                ]
            )
            try:
                result = subprocess.run(
                    argv,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError(
                    f"Codex CLI timed out after {self.timeout_seconds:.0f}s"
                ) from exc

            if result.returncode != 0:
                stderr = (result.stderr or "").strip()
                stdout = (result.stdout or "").strip()
                detail = stderr or stdout or "no output"
                raise RuntimeError(f"Codex CLI failed with exit code {result.returncode}: {detail[-2000:]}")

            content = ""
            if output_path.exists():
                content = output_path.read_text(encoding="utf-8").strip()
            if not content:
                content = self._fallback_stdout(result.stdout)
            if stop:
                content = self._apply_stop(content, stop)

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    @staticmethod
    def _messages_to_prompt(messages: list[BaseMessage]) -> str:
        rendered: list[str] = [
            "You are being called as AIMiner's local Codex LLM provider.",
            "Return only the final assistant response requested by the messages.",
            "Do not edit files or run commands unless the message explicitly asks for analysis that requires it.",
            "",
        ]
        for message in messages:
            role = getattr(message, "type", "message")
            content = CodexChatModel._content_to_text(message.content)
            rendered.append(f"<{role}>")
            rendered.append(content)
            rendered.append(f"</{role}>")
            rendered.append("")
        return "\n".join(rendered).strip() + "\n"

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
            return "\n".join(parts)
        return str(content)

    @staticmethod
    def _fallback_stdout(stdout: str | None) -> str:
        lines = [line.strip() for line in (stdout or "").splitlines() if line.strip()]
        return lines[-1] if lines else ""

    @staticmethod
    def _apply_stop(content: str, stop: list[str]) -> str:
        cut_at: int | None = None
        for marker in stop:
            index = content.find(marker)
            if index >= 0:
                cut_at = index if cut_at is None else min(cut_at, index)
        return content if cut_at is None else content[:cut_at]
