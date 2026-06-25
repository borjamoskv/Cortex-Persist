# [C5-REAL] Exergy-Maximized
import re
import time

from typing import Any

try:
    from google.antigravity import hooks # type: ignore
except ImportError:
    pass

class _HookResult:
    PROCEED: Any = None
HookResult = _HookResult

from legacy_research.observability.telemetry import telemetry

_timers = {}


def _extract_skill_info(data) -> dict:
    """
    Robust extraction of skill name and source from tool call data.
    """
    try:
        if data.name == "view_file":
            path = data.arguments.get("AbsolutePath", "")
            match = re.search(r"skills/([^/]+)/SKILL\.md", path)
            if match:
                return {"skill": match.group(1), "source": "skill_md"}
            match_workflow = re.search(r"workflows/([^/]+)\.md", path)
            if match_workflow:
                return {"skill": match_workflow.group(1), "source": "workflow"}

        elif data.name.startswith("mcp_") or "call_mcp_tool" in data.name:
            server_name = data.arguments.get("ServerName", data.name.replace("mcp_", ""))
            return {"skill": f"MCP_{server_name.upper()}", "source": "mcp"}

    except Exception as exc:
        import logging

        logging.warning("Suppressed exception: %s", exc)

    return {"skill": data.name or "UNKNOWN", "source": "programmatic"}


@hooks.pre_tool_call_decide
async def track_start(data) -> HookResult:
    info = _extract_skill_info(data)

    # Use agent's conversation ID as session ID
    session_id = getattr(data, "conversation_id", "unknown_session")
    call_id = data.id

    _timers[call_id] = {
        "start": time.time(),
        "skill": info["skill"],
        "source": info["source"],
        "session_id": session_id,
    }

    telemetry.log_event(
        session_id=session_id,
        call_id=call_id,
        skill=info["skill"],
        source=info["source"],
        event_type="tool_start",
    )

    return HookResult.PROCEED


@hooks.post_tool_call
async def track_end(data):
    if data.id in _timers:
        timer = _timers.pop(data.id)
        duration_ms = int((time.time() - timer["start"]) * 1000)
        success = not getattr(data, "error", False)

        telemetry.log_event(
            session_id=timer["session_id"],
            call_id=data.id,
            skill=timer["skill"],
            source=timer["source"],
            event_type="tool_end",
            duration_ms=duration_ms,
            success=success,
        )


@hooks.on_tool_error
async def track_error(context, error, data=None):
    if data and hasattr(data, "id") and data.id in _timers:
        timer = _timers.pop(data.id)
        duration_ms = int((time.time() - timer["start"]) * 1000)

        telemetry.log_event(
            session_id=timer["session_id"],
            call_id=data.id,
            skill=timer["skill"],
            source=timer["source"],
            event_type="tool_end",
            duration_ms=duration_ms,
            success=False,
            error_msg=str(error),
        )
