"""
tests/test_deploy_skill.py - Tests for DeploySkill Event V1 migration.

Verifies:
- @register('deploy') lands in registry
- execute() returns dict artifact (IO contract)
- artifact is JSON-serializable (no sys.exit, no prints)
- trace_id from event propagates to artifact
- unknown command returns error artifact (not exception)
"""
import json
import pytest

from schema.event_v1 import EventV1
from skills.registry import resolve, list_skills, RegistryLockError

# Import to trigger @register side effect
import skills.deploy  # noqa: F401


def _make_event(command: str, **kwargs) -> EventV1:
    return EventV1(
        event_type="command_received",
        source="test",
        skill_id="deploy",
        payload={"command": command, **kwargs},
    )


def test_deploy_skill_is_registered() -> None:
    """@register('deploy') must land in registry after import."""
    assert "deploy" in list_skills()


def test_deploy_skill_resolves_from_event() -> None:
    """resolve(event) must return DeploySkill class."""
    event = _make_event("validate")
    skill_class = resolve(event)
    assert skill_class.__name__ == "DeploySkill"


def test_deploy_execute_returns_dict() -> None:
    """execute() must return a dict (IO contract)."""
    event = _make_event("validate")
    skill_class = resolve(event)
    result = skill_class().execute(event)
    assert isinstance(result, dict)


def test_deploy_artifact_is_json_serializable() -> None:
    """Artifact must be JSON-serializable (no sys.exit, no complex types)."""
    event = _make_event("validate")
    skill_class = resolve(event)
    artifact = skill_class().execute(event)
    # must not raise
    json.dumps(artifact)


def test_deploy_trace_id_propagates() -> None:
    """trace_id from event must appear in artifact."""
    event = _make_event("validate")
    skill_class = resolve(event)
    artifact = skill_class().execute(event)
    assert artifact["trace_id"] == event.trace_id


def test_deploy_unknown_command_returns_error_not_exception() -> None:
    """Unknown command must return error artifact, never raise."""
    event = _make_event("xyzzy-unknown")
    skill_class = resolve(event)
    artifact = skill_class().execute(event)
    assert artifact["status"] == "error"
    assert "command" in artifact
    assert artifact["command"] == "xyzzy-unknown"


def test_deploy_artifact_has_required_keys() -> None:
    """Artifact must always have the canonical keys."""
    required_keys = {"command", "status", "report", "issues", "detail", "trace_id"}
    for cmd in ["validate", "bootstrap-db", "manifest", "xyzzy"]:
        event = _make_event(cmd)
        skill_class = resolve(event)
        artifact = skill_class().execute(event)
        assert required_keys.issubset(artifact.keys()), (
            f"Missing keys for command='{cmd}': {required_keys - artifact.keys()}"
        )
