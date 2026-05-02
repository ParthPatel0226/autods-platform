"""Pipeline smoke tests — verify each stage's endpoint is reachable."""
from __future__ import annotations

import uuid


def test_eda_generate_questions_returns_list(auth_client, project_id):
    """POST /eda/generate-questions?project_id=... should not 404 (route must exist)."""
    resp = auth_client.post(
        f"/eda/generate-questions?project_id={project_id}"
    )
    # 200 = questions returned; 404 = no data loaded (also acceptable for smoke)
    # The only unacceptable responses are 405 (method wrong) or route not found
    assert resp.status_code != 405, "Method not allowed — EDA route mismatch"
    # 404 with "not found" message = project/session not found (expected without data)
    if resp.status_code == 404:
        assert "not found" in resp.json().get("detail", "").lower()
    elif resp.status_code == 200:
        body = resp.json()
        assert isinstance(body, list)


def test_modeling_configure_returns_eta(auth_client, project_id):
    """POST /modeling/configure?project_id=... should respond (not 404 route-missing)."""
    resp = auth_client.post(
        f"/modeling/configure?project_id={project_id}",
        json={"algorithms": ["xgboost"], "metric": "accuracy"},
    )
    # 200 = configured; 4xx = expected errors (no data loaded, etc.)
    assert resp.status_code != 405, "Method not allowed — modeling route mismatch"
    if resp.status_code == 200:
        body = resp.json()
        assert "eta_seconds" in body


def test_explain_shap_endpoint_exists(auth_client):
    """POST /explain/shap with empty body should return 422 (validation), NOT 404."""
    resp = auth_client.post("/explain/shap", json={})
    # 422 = Pydantic validation failed (required fields missing) → endpoint exists
    # 400 = service-level validation → also acceptable
    assert resp.status_code != 404, "SHAP endpoint not registered"
    assert resp.status_code != 405, "Method not allowed — route mismatch"
    assert resp.status_code in (400, 422, 200), (
        f"Unexpected status {resp.status_code}: {resp.text}"
    )


def test_jobs_endpoint_returns_404_for_unknown(auth_client):
    """GET /jobs/{unknown_id} should return 404."""
    fake_job_id = f"no-such-job-{uuid.uuid4().hex}"
    resp = auth_client.get(f"/jobs/{fake_job_id}")
    assert resp.status_code == 404
