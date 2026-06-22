"""Tests for the RepoHealthSkill mapping."""

import json
from dataclasses import asdict

from schema.event_v1 import EventV1
from skills.registry import list_skills, resolve
from skills.repo_health import RepoHealthSkill


def test_repo_health_skill_is_registered():
    """Verify @register adds the skill to the registry."""
    skills = list_skills()
    assert "repo_health" in skills


def test_repo_health_skill_resolves_from_event():
    """Verify EventV1 payload resolves to the correct class."""
    event = EventV1(
        event_type="command", source="test", skill_id="repo_health", payload={"command": "check"}
    )
    skill_class = resolve(event)
    assert skill_class is RepoHealthSkill


def test_repo_health_execute_returns_dict():
    """Verify execution IO contract returns a dict."""
    event = EventV1(
        event_type="command", source="test", skill_id="repo_health", payload={"command": "check"}
    )
    skill = RepoHealthSkill()
    artifact = skill.execute(event)
    assert isinstance(artifact, dict)


def test_repo_health_artifact_is_json_serializable():
    """Verify the artifact dict has no exotic objects (JSON clean)."""
    event = EventV1(
        event_type="command", source="test", skill_id="repo_health", payload={"command": "check"}
    )
    skill = RepoHealthSkill()
    artifact = skill.execute(event)
    try:
        json.dumps(artifact)
    except TypeError as e:
        raise AssertionError(f"Artifact is not JSON serializable: {e}")


def test_repo_health_trace_id_propagates():
    """Verify the trace_id in the event propagates to the artifact."""
    trace = "trace_abc123"
    event = EventV1(
        event_type="command",
        source="test",
        skill_id="repo_health",
        payload={"command": "check"},
        trace_id=trace,
    )
    skill = RepoHealthSkill()
    artifact = skill.execute(event)
    assert artifact.get("trace_id") == trace


def test_repo_health_unknown_command_returns_error_not_exception():
    """Verify unknown commands yield an error artifact, not an unhandled exception."""
    event = EventV1(
        event_type="command",
        source="test",
        skill_id="repo_health",
        payload={"command": "made_up_command"},
    )
    skill = RepoHealthSkill()
    artifact = skill.execute(event)

    assert artifact["status"] == "error"
    assert "unknown command" in artifact["detail"]["error"]


def test_repo_health_artifact_has_required_keys():
    """Verify the returned artifact has the canonical 6 keys."""
    event = EventV1(
        event_type="command", source="test", skill_id="repo_health", payload={"command": "check"}
    )
    skill = RepoHealthSkill()
    artifact = skill.execute(event)

    expected_keys = {"command", "status", "report", "issues", "detail", "trace_id"}
    assert set(artifact.keys()) == expected_keys
