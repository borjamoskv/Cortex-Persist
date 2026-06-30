# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from babylon60.observability.ingestor import (
    _extract_skill_info,
    _duration_ms,
    _parse_timestamp,
    _parse_completed_at,
    _analyze_steps,
    _compute_funnel_states,
    _calculate_session_duration,
    _parse_outcome_score,
    _parse_single_transcript,
    _compute_cronos_records,
    _compile_stats,
    _write_cronos_report,
)


def test_extract_skill_info() -> None:
    res = _extract_skill_info("view_file", {"AbsolutePath": "/some/path/skills/my_skill/SKILL.md"})
    assert res == {"skill": "my_skill", "source": "skill_md"}

    res_wf = _extract_skill_info("view_file", {"AbsolutePath": "/some/path/workflows/my_wf.md"})
    assert res_wf == {"skill": "my_wf", "source": "workflow"}

    res_mcp = _extract_skill_info(
        "call_mcp_tool", {"ServerName": "my_server", "ToolName": "my_tool"}
    )
    assert res_mcp == {"skill": "MCP_MY_SERVER", "source": "mcp", "mcp_tool": "my_tool"}

    res_mcp_direct = _extract_skill_info("mcp_server_tool", {})
    assert res_mcp_direct == {"skill": "MCP_SERVER", "source": "mcp"}

    res_builtin = _extract_skill_info("grep_search", {})
    assert res_builtin == {"skill": "grep_search", "source": "builtin"}

    res_unknown = _extract_skill_info("nonexistent_tool", {})
    assert res_unknown == {"skill": "nonexistent_tool", "source": "unknown"}


def test_duration_ms() -> None:
    assert _duration_ms("2026-06-09T05:00:00Z", "2026-06-09T05:00:10Z") == 10000
    assert _duration_ms("invalid", "2026-06-09T05:00:10Z") is None


def test_parse_timestamps() -> None:
    assert (
        _parse_timestamp("Created At: 2026-06-09T05:00:00Z\nSome other text")
        == "2026-06-09T05:00:00Z"
    )
    assert (
        _parse_completed_at("Completed At: 2026-06-09T05:00:10Z\nSome other text")
        == "2026-06-09T05:00:10Z"
    )
    assert _parse_timestamp(None) is None
    assert _parse_completed_at("") is None


def test_analyze_steps() -> None:
    lines = [
        {
            "tool_calls": [
                {"name": "view_file", "args": {"AbsolutePath": "/some/path/workflows/foo.md"}}
            ]
        },
        {"source": "USER_EXPLICIT", "content": "/bar workflow"},
    ]
    workflow_meta = {"foo": 10, "bar": 15}
    viewed, referenced, non_wf, artifacts = _analyze_steps(lines, workflow_meta)
    assert viewed == {"foo"}
    assert referenced == {"bar"}
    assert non_wf == 0
    assert artifacts == 0


def test_compute_funnel_states() -> None:
    res = _compute_funnel_states(
        viewed_workflows={"foo"},
        referenced_workflows={"bar"},
        non_wf_tool_calls=3,
        artifacts_generated=1,
        success=True,
    )
    assert "foo" in res
    assert res["foo"]["state"] == "VIEWED"
    assert res["foo"]["execution_score"] == 1.0

    assert "bar" in res
    assert res["bar"]["state"] == "COMPLETED"
    assert res["bar"]["execution_score"] == 21.5  # 1.0 + 2.0 + 5.0 + 0.5*3 + 2.0*1 + 10.0


def test_calculate_session_duration() -> None:
    lines = [
        {"created_at": "2026-06-09T05:00:00Z", "content": "Created At: 2026-06-09T05:00:00Z"},
        {"created_at": "2026-06-09T05:10:00Z", "content": "Completed At: 2026-06-09T05:10:00Z"},
    ]
    duration, start_dt = _calculate_session_duration(lines)
    assert duration == 10.0
    assert start_dt is not None
    assert start_dt.year == 2026


def test_parse_outcome_score() -> None:
    lines = [{"source": "USER_EXPLICIT", "content": "Score is /score 9.5"}]
    assert _parse_outcome_score(lines) == 9.5
    assert _parse_outcome_score([]) == 1.0


def test_parse_single_transcript_and_cronos(tmp_path: Path) -> None:
    transcript_path = (
        tmp_path / "brain" / "session_1" / ".system_generated" / "logs" / "transcript.jsonl"
    )
    transcript_path.parent.mkdir(parents=True, exist_ok=True)

    steps = [
        {
            "created_at": "2026-06-09T05:00:00Z",
            "content": "Created At: 2026-06-09T05:00:00Z",
            "source": "USER_EXPLICIT",
        },
        {
            "tool_calls": [
                {"name": "view_file", "args": {"AbsolutePath": "/some/path/workflows/my_wf.md"}}
            ]
        },
        {"source": "USER_EXPLICIT", "content": "/my_wf is starting now"},
        {
            "status": "DONE",
            "created_at": "2026-06-09T05:10:00Z",
            "content": "Completed At: 2026-06-09T05:10:00Z",
        },
    ]
    with open(transcript_path, "w", encoding="utf-8") as fh:
        for step in steps:
            fh.write(json.dumps(step) + "\n")

    workflow_meta = {"my_wf": 15}
    res = _parse_single_transcript(str(transcript_path), workflow_meta)
    assert res is not None
    assert res["session_id"] == "session_1"
    assert "my_wf" in res["workflows"]
    assert res["workflows"]["my_wf"]["state"] == "REFERENCED"

    # test compute_cronos_records
    records = _compute_cronos_records([res], workflow_meta, rolling_window=5)
    assert len(records) == 1
    assert records[0]["workflow"] == "my_wf"
    assert records[0]["state"] == "REFERENCED"

    # test compile_stats
    stats = _compile_stats(records)
    assert "my_wf" in stats
    assert stats["my_wf"]["viewed"] == 1

    # test write_cronos_report
    report_path = tmp_path / "cronos_report.md"
    _write_cronos_report(stats, str(report_path))
    assert report_path.exists()
