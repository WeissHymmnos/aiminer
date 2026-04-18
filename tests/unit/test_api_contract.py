import importlib
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
