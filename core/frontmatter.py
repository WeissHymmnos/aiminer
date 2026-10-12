"""Lightweight Markdown frontmatter parser and serializer.

Avoids external heavy dependencies while safely handling scalar and
flow-list values (e.g. tags: [a, b], status: "proven") for both
the LLMWiki vault and the FastAPI workstation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Standard metadata ordering for clean diffs and readability
_PREFERRED_KEYS = (
    "title",
    "slug",
    "type",
    "status",
    "summary",
    "updated",
    "tags",
    "related",
)


def parse_frontmatter(source: str | Path) -> tuple[dict[str, Any], str]:
    """Parse YAML-style frontmatter from a string or file path.

    Returns:
        (metadata_dict, body_text)
    """
    if isinstance(source, Path):
        try:
            text = source.read_text(encoding="utf-8")
        except Exception:
            return {}, ""
    else:
        text = str(source)

    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text

    meta: dict[str, Any] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        if not k:
            continue

        if v.startswith("[") and v.endswith("]"):
            items = [s.strip().strip('"').strip("'") for s in v[1:-1].split(",")]
            meta[k] = [s for s in items if s]
        elif v.lower() == "true":
            meta[k] = True
        elif v.lower() == "false":
            meta[k] = False
        else:
            meta[k] = v.strip('"').strip("'")

    body = text[m.end():]
    return meta, body


def dump_frontmatter(meta: dict[str, Any], body: str = "") -> str:
    """Serialize a metadata dictionary into a YAML frontmatter block.

    Maintains a deterministic key order for version control stability.
    """
    lines = ["---"]

    def _format_entry(k: str, v: Any) -> str:
        if isinstance(v, (list, tuple)):
            items = ", ".join(f'"{str(x).replace(chr(34), chr(92) + chr(34))}"' for x in v)
            return f"{k}: [{items}]"
        if isinstance(v, bool):
            return f"{k}: {str(v).lower()}"
        if isinstance(v, (int, float)):
            return f"{k}: {v}"
        safe = str(v).replace('"', '\\"').replace("\n", " ")
        return f'{k}: "{safe}"'

    # 1. Output preferred keys first
    for k in _PREFERRED_KEYS:
        if k in meta:
            lines.append(_format_entry(k, meta[k]))

    # 2. Output remaining extra keys in sorted order
    for k in sorted(meta.keys()):
        if k not in _PREFERRED_KEYS:
            lines.append(_format_entry(k, meta[k]))

    lines.append("---")
    header = "\n".join(lines) + "\n\n"
    return header + body if body else header
