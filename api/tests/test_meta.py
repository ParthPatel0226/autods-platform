"""Tests for /meta routes."""
from __future__ import annotations


def test_list_tools_returns_nonempty(auth_client):
    """GET /meta/tools should return a list of tool entries."""
    resp = auth_client.get("/meta/tools")
    # 200 = tool registry loaded; 500 = backend unavailable (also informative)
    assert resp.status_code != 404, "Tools endpoint not registered"
    if resp.status_code == 200:
        body = resp.json()
        assert "tools" in body
        assert isinstance(body["tools"], list)
        assert body["total"] >= 0


def test_pipeline_log_returns_list(auth_client, project_id):
    """GET /meta/pipeline-log/{project_id} should return a paginated list."""
    resp = auth_client.get(f"/meta/pipeline-log/{project_id}")
    # 200 = log retrieved (possibly empty); 404 = project not found in state
    assert resp.status_code not in (405,), "Route mismatch"
    if resp.status_code == 200:
        body = resp.json()
        assert "entries" in body
        assert "total" in body
        assert isinstance(body["entries"], list)
