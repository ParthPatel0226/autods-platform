"""Tests for /health and / meta endpoints."""
from __future__ import annotations


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "uptime_seconds" in body


def test_root_returns_name(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "AutoDS API"
    assert "docs" in body
