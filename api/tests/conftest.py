"""Shared pytest fixtures for api/ tests."""
from __future__ import annotations

# All versioned routes live under this prefix.  Infrastructure routes
# (/health, /) remain at the root and should NOT use this prefix.
V1 = "/v1"

import pytest
from fastapi.testclient import TestClient

from api.main import app


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    """Plain (unauthenticated) TestClient."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="session")
def auth_client():
    """TestClient with dev-bypass bearer token pre-set."""
    with TestClient(app, raise_server_exceptions=False) as c:
        c.headers["Authorization"] = "Bearer dev"
        yield c


# ---------------------------------------------------------------------------
# Data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_csv() -> bytes:
    """Tiny valid CSV as bytes."""
    return (
        b"age,income,label\n"
        b"25,50000,1\n"
        b"30,60000,0\n"
        b"35,70000,1\n"
        b"40,80000,0\n"
        b"45,90000,1\n"
    )


# ---------------------------------------------------------------------------
# Project fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def project_id(auth_client):
    """Create a project, yield its project_id, delete it afterward."""
    resp = auth_client.post(f"{V1}/projects/", json={"name": "pytest-project"})
    assert resp.status_code == 201, f"Could not create project: {resp.text}"
    pid = resp.json()["project_id"]
    yield pid
    # cleanup — best-effort
    auth_client.delete(f"{V1}/projects/{pid}")
