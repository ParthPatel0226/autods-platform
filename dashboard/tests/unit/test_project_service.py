"""Unit tests for dashboard.components.project_service.

All session_manager calls are mocked so no file-system I/O occurs.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_sm(**overrides):
    """Return a MagicMock that satisfies the session_manager API."""
    m = MagicMock()
    m.save_session.return_value = "ok"
    m.session_exists.return_value = True
    m.list_sessions.return_value = []
    m.delete_session.return_value = True
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


def _make_project_state(user_id: str = "local", **extra) -> dict:
    """Build a minimal project_meta payload as stored by _persist."""
    from dashboard.components.project_service import Project

    p = Project(name="Test", user_id=user_id)
    meta = p.to_dict()
    meta.update(extra)
    return {
        "project_meta": json.dumps(meta),
        "detected_domain": "",
        "problem_type": "",
        "workflow_status": "draft",
        "completed_steps": [],
        "target_column": "",
        "analysis_mode": "guided",
    }


# ---------------------------------------------------------------------------
# Project dataclass
# ---------------------------------------------------------------------------


def test_project_defaults():
    from dashboard.components.project_service import Project, _STEP_KEYS

    p = Project()
    assert p.name == "Untitled Project"
    assert p.user_id == "local"
    assert p.status == "draft"
    assert set(p.step_status.keys()) == set(_STEP_KEYS)
    assert all(v == "pending" for v in p.step_status.values())


def test_project_to_dict_round_trip():
    from dashboard.components.project_service import Project

    p = Project(name="Round Trip", user_id="user@test.com")
    d = p.to_dict()
    p2 = Project.from_dict(d)
    assert p2.name == p.name
    assert p2.id == p.id
    assert p2.user_id == p.user_id


def test_project_from_dict_ignores_unknown_keys():
    from dashboard.components.project_service import Project

    p = Project(name="X")
    d = p.to_dict()
    d["nonexistent_field"] = "should_be_ignored"
    p2 = Project.from_dict(d)
    assert p2.name == "X"


# ---------------------------------------------------------------------------
# _extract_meta
# ---------------------------------------------------------------------------


def test_extract_meta_from_json_string():
    from dashboard.components.project_service import Project, _extract_meta

    p = Project(name="Meta Test")
    state = {"project_meta": json.dumps(p.to_dict())}
    result = _extract_meta(state)
    assert result is not None
    assert result["name"] == "Meta Test"


def test_extract_meta_from_dict():
    from dashboard.components.project_service import Project, _extract_meta

    p = Project(name="Dict Meta")
    state = {"project_meta": p.to_dict()}
    result = _extract_meta(state)
    assert result["name"] == "Dict Meta"


def test_extract_meta_missing_returns_none():
    from dashboard.components.project_service import _extract_meta

    assert _extract_meta({}) is None
    assert _extract_meta({"project_meta": None}) is None
    assert _extract_meta({"project_meta": "bad json!!!"}) is None


# ---------------------------------------------------------------------------
# create / get / save / delete
# ---------------------------------------------------------------------------


def test_create_persists_and_returns_project():
    from dashboard.components.project_service import create

    sm = _mock_sm()
    with patch("dashboard.components.project_service.session_manager", sm, create=True):
        with patch("session.session_manager", sm, create=True):
            p = create(name="My Project", user_id="u1")

    assert p.name == "My Project"
    assert p.user_id == "u1"
    sm.save_session.assert_called_once()
    call_args = sm.save_session.call_args
    assert call_args[0][0] == p.id  # first positional arg is session_id


def test_get_returns_project_when_exists():
    from dashboard.components.project_service import Project, get

    p = Project(name="Existing")
    state = _make_project_state()
    state["project_meta"] = json.dumps(p.to_dict())

    sm = _mock_sm()
    sm.session_exists.return_value = True
    sm.load_session.return_value = state

    with patch("session.session_manager", sm, create=True):
        result = get(p.id)

    assert result is not None
    assert result.id == p.id


def test_get_returns_none_when_not_found():
    from dashboard.components.project_service import get

    sm = _mock_sm()
    sm.session_exists.return_value = False

    with patch("session.session_manager", sm, create=True):
        result = get("nonexistent-id")

    assert result is None


def test_delete_delegates_to_session_manager():
    from dashboard.components.project_service import delete

    sm = _mock_sm()
    sm.delete_session.return_value = True

    with patch("session.session_manager", sm, create=True):
        result = delete("some-id")

    assert result is True
    sm.delete_session.assert_called_once_with("some-id")


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


def test_list_all_filters_by_user_id():
    from dashboard.components.project_service import Project, list_all

    p1 = Project(name="User1 Project", user_id="user1")
    p2 = Project(name="User2 Project", user_id="user2")

    summaries = [{"session_id": p1.id}, {"session_id": p2.id}]
    states = {
        p1.id: {"project_meta": json.dumps(p1.to_dict())},
        p2.id: {"project_meta": json.dumps(p2.to_dict())},
    }

    sm = _mock_sm()
    sm.list_sessions.return_value = summaries
    sm.load_session.side_effect = lambda sid: states[sid]

    with patch("session.session_manager", sm, create=True):
        results = list_all(user_id="user1")

    assert len(results) == 1
    assert results[0].name == "User1 Project"


def test_list_all_sorted_newest_first():
    from dashboard.components.project_service import Project, list_all

    p_old = Project(name="Old", user_id="local")
    p_old.updated_at = "2024-01-01T00:00:00+00:00"
    p_new = Project(name="New", user_id="local")
    p_new.updated_at = "2025-06-01T00:00:00+00:00"

    summaries = [{"session_id": p_old.id}, {"session_id": p_new.id}]
    states = {
        p_old.id: {"project_meta": json.dumps(p_old.to_dict())},
        p_new.id: {"project_meta": json.dumps(p_new.to_dict())},
    }

    sm = _mock_sm()
    sm.list_sessions.return_value = summaries
    sm.load_session.side_effect = lambda sid: states[sid]

    with patch("session.session_manager", sm, create=True):
        results = list_all(user_id="local")

    assert results[0].name == "New"
    assert results[1].name == "Old"
