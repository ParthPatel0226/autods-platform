"""Tests for /projects routes."""
from __future__ import annotations

import uuid

V1 = "/v1"


def test_create_project(auth_client):
    """POST /projects/ should create a project and return project_id."""
    resp = auth_client.post(f"{V1}/projects/", json={"name": "my-test-project"})
    assert resp.status_code == 201
    body = resp.json()
    assert "project_id" in body
    pid = body["project_id"]
    assert pid  # non-empty
    # cleanup
    auth_client.delete(f"{V1}/projects/{pid}")


def test_list_projects(auth_client):
    """GET /projects/ should return a list."""
    resp = auth_client.get(f"{V1}/projects/")
    assert resp.status_code == 200
    body = resp.json()
    # response is either a list or a dict with a list field
    assert isinstance(body, (list, dict))


def test_get_nonexistent_returns_404(auth_client):
    """GET /projects/{id} for unknown ID should return 404."""
    fake_id = f"nonexistent-{uuid.uuid4().hex}"
    resp = auth_client.get(f"{V1}/projects/{fake_id}")
    assert resp.status_code == 404


def test_delete_project(auth_client, project_id):
    """DELETE /projects/{id} should remove the project."""
    resp = auth_client.delete(f"{V1}/projects/{project_id}")
    assert resp.status_code in (200, 204)
    # verify it's gone
    get_resp = auth_client.get(f"{V1}/projects/{project_id}")
    assert get_resp.status_code == 404
