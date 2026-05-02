"""Tests for /auth routes."""
from __future__ import annotations

import uuid


def _unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


def test_signup_returns_token(client):
    """POST /auth/signup should return a token in internal (dev) mode."""
    resp = client.post(
        "/auth/signup",
        json={
            "email": _unique_email(),
            "password": "password123",
            "full_name": "Test User",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["access_token"]


def test_login_returns_token(client):
    """POST /auth/login should return a token in internal (dev) mode."""
    resp = client.post(
        "/auth/login",
        json={"email": _unique_email(), "password": "password123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["access_token"]


def test_me_requires_auth(client):
    """GET /auth/me without Authorization header should be rejected."""
    resp = client.get("/auth/me")
    assert resp.status_code in (401, 403)


def test_me_returns_user(auth_client):
    """GET /auth/me with dev-bypass token should return user info."""
    resp = auth_client.get("/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert "user_id" in body
    assert body["user_id"]  # non-empty
