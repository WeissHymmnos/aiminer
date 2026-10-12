"""Robust JSON parser for LLM-generated structured outputs.

Standardizes JSON extraction and schema validation across all agents.
Handles common LLM formatting quirks:
- Markdown code blocks (```json ... ``` or ``` ... ```)
- Raw control characters (newlines, tabs) inside string literals
- LaTeX mathematical formulas with unescaped backslashes (e.g., \\alpha, \\frac)
- Seamless validation into Pydantic models with clear error telemetry
"""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]")
_LATEX_BACKSLASH_RE = re.compile(r'(?<!\\)\\(?!(?:["\\/]|u[0-9a-fA-F]{4}))')


def strip_markdown_json(text: str) -> str:
    """Remove markdown code block wrappers and strip invalid control characters."""
    text = text.strip()
    if text.startswith("```json"):
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    elif text.startswith("```"):
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    # Replace forbidden control characters with spaces
    text = _CONTROL_CHAR_RE.sub(" ", text)
    return text.strip()


def escape_control_chars_in_strings(text: str) -> str:
    """Escape raw \\n, \\t, \\r inside JSON string literals.

    Tracks string boundaries via unescaped double-quote matching.
    """
    out: list[str] = []
    in_string = False
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if ch == '"' and (i == 0 or text[i - 1] != "\\"):
            in_string = not in_string
            out.append(ch)
        elif in_string and ch == "\n":
            out.append("\\n")
        elif in_string and ch == "\t":
            out.append("\\t")
        elif in_string and ch == "\r":
            out.append("\\r")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def parse_llm_json(text: str) -> dict[str, Any]:
    """Parse a JSON object emitted by an LLM with progressive error recovery.

    Pydantic's strict RFC-8259 parser rejects literal control characters
    inside string values (e.g. multi-line LaTeX formulas). This function
    normalizes the string and uses Python's lenient stdlib parser before
    returning a clean dictionary.
    """
    cleaned = strip_markdown_json(text)

    # 1. First attempt: lenient parse (accepts literal control characters in strings)
    try:
        return json.loads(cleaned, strict=False)
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Second attempt: fix stray single backslashes common in LaTeX formulas
    # (e.g., "\alpha" -> "\\alpha")
    fixed = _LATEX_BACKSLASH_RE.sub(r"\\\\", cleaned)
    try:
        return json.loads(fixed, strict=False)
    except (json.JSONDecodeError, ValueError):
        pass

    # 3. Third attempt: escape remaining raw control characters inside string literals
    escaped = escape_control_chars_in_strings(fixed)
    try:
        return json.loads(escaped, strict=False)
    except (json.JSONDecodeError, ValueError) as err:
        raise ValueError(
            f"Failed to parse LLM JSON response: {err}. Raw input snippet: {cleaned[:200]!r}"
        ) from err


def parse_llm_model(text: str, model_cls: type[T]) -> T:
    """Parse LLM output directly into a validated Pydantic model.

    Bypasses Pydantic's strict RFC-8259 JSON parser by running
    parse_llm_json first, then validating the resulting dict.
    """
    parsed_dict = parse_llm_json(text)
    return model_cls.model_validate(parsed_dict)
