from __future__ import annotations

from core.wiki import LLMWiki


def main() -> None:
    wiki = LLMWiki()
    result = wiki.upgrade_to_graph_schema(dry_run=False)
    print(
        f"Upgraded {len(result['upgraded'])} pages; skipped {len(result['skipped'])} pages."
    )


if __name__ == "__main__":
    main()
