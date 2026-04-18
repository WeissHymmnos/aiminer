import importlib
import json
import os


os.environ["AIMINER_DISABLE_AUTH"] = "true"

import api  # noqa: E402


def _module():
    return importlib.reload(api)


def test_results_endpoint_returns_paginated_shape():
    mod = _module()
    payload = mod.get_results(run_id=None, offset=0, limit=10)
    assert {"items", "total", "offset", "next_offset"} <= set(payload.keys())
    if payload["items"]:
        assert {"selection_score", "best_strategy_id"} <= set(payload["items"][0].keys())


def test_wiki_index_returns_paginated_shape():
    mod = _module()
    payload = mod.wiki_index(offset=0, limit=10)
    assert {"items", "total", "offset", "next_offset"} <= set(payload.keys())


def test_wiki_graph_returns_nodes_and_edges():
    mod = _module()
    payload = mod.wiki_graph()
    assert "nodes" in payload
    assert "edges" in payload


def test_swarm_status_available_when_auth_disabled():
    mod = _module()
    actor = mod.Actor(identity="auth-disabled")
    payload = mod.swarm_status(actor=actor)
    assert "running_count" in payload


def test_swarm_logs_tail_returns_recent_entries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "results" / "swarm_runs"
    run_dir.mkdir(parents=True)
    (run_dir / "run_1.json").write_text("{}", encoding="utf-8")
    (run_dir / "run_1.jsonl").write_text(
        "\n".join(
            json.dumps({"message": f"log-{index}", "timestamp": f"00:00:0{index}"})
            for index in range(5)
        ),
        encoding="utf-8",
    )

    mod = _module()
    actor = mod.Actor(identity="auth-disabled")
    payload = mod.get_swarm_run_logs("run_1", offset=0, limit=2, tail=True, actor=actor)

    assert [item["message"] for item in payload["items"]] == ["log-3", "log-4"]
    assert payload["offset"] == 3
    assert payload["next_offset"] == 5


def test_frontend_fallback_uses_frontend_dist_build_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    frontend_dist = tmp_path / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    html = "<!doctype html><html><body>frontend ok</body></html>"
    (frontend_dist / "index.html").write_text(html, encoding="utf-8")

    mod = _module()
    response = mod.frontend_fallback("wiki")

    assert response.body.decode("utf-8") == html
