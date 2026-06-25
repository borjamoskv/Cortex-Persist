# [C5-REAL] Exergy-Maximized
"""
CORTEX Transcript Ingestor v2 — Positional Correlation

Architecture:
  transcript.jsonl steps follow this pattern:
    Step N:   PLANNER_RESPONSE with tool_calls=[call_0, call_1, ..., call_K]
    Step N+1: Result for call_0
    Step N+2: Result for call_1
    ...
    Step N+K: Result for call_K

  Correlation is positional: call[i] in the PLANNER_RESPONSE maps to step[N+1+i].

  Each call emits a tool_start event (from the PLANNER_RESPONSE).
  Each result emits a tool_end event (from the result step).
  call_id is deterministic: "{session_id}_{planner_step}_{i}" where i is the index
  within the tool_calls array.
"""

import logging

logger = logging.getLogger("cortex.exergy")
import glob
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from legacy_research.observability.telemetry import CortexTelemetry

LOG_FILE = os.path.expanduser("~/.gemini/config/skills/_metrics/runtime_events.jsonl")


def _extract_skill_info(tool_name: str, tool_args: dict) -> dict:
    """
    Deterministic skill extraction from tool call data.

    Returns {"skill": str, "source": str} where source is one of:
      skill_md, workflow, mcp, builtin

    Never returns silently — always classifies.
    """
    if tool_name == "view_file":
        path = tool_args.get("AbsolutePath", "")
        match = re.search("skills/([^/]+)/SKILL\\.md", path)
        if match:
            return {"skill": match.group(1), "source": "skill_md"}
        match_wf = re.search("workflows/([^/]+)\\.md", path)
        if match_wf:
            return {"skill": match_wf.group(1), "source": "workflow"}
    if tool_name == "call_mcp_tool":
        server = tool_args.get("ServerName", "unknown")
        tool = tool_args.get("ToolName", "unknown")
        return {"skill": f"MCP_{server.upper()}", "source": "mcp", "mcp_tool": tool}
    if tool_name.startswith("mcp_"):
        server = tool_name.replace("mcp_", "").split("_")[0]
        return {"skill": f"MCP_{server.upper()}", "source": "mcp"}
    builtins = {
        "view_file",
        "list_dir",
        "grep_search",
        "run_command",
        "write_to_file",
        "replace_file_content",
        "multi_replace_file_content",
        "search_web",
        "read_url_content",
        "invoke_subagent",
        "manage_subagents",
        "send_message",
        "ask_question",
        "generate_image",
        "schedule",
        "manage_task",
        "ask_permission",
        "list_permissions",
    }
    if tool_name in builtins:
        return {"skill": tool_name, "source": "builtin"}
    return {"skill": tool_name or "UNKNOWN", "source": "unknown"}


def _parse_timestamp(content: str) -> str | None:
    """Extract 'Created At' timestamp from step content."""
    if not content:
        return None
    match = re.search("Created At:\\s*(\\S+)", content)
    if match:
        return match.group(1)
    return None


def _parse_completed_at(content: str) -> str | None:
    """Extract 'Completed At' timestamp from step content."""
    if not content:
        return None
    match = re.search("Completed At:\\s*(\\S+)", content)
    if match:
        return match.group(1)
    return None


def _duration_ms(start_iso: str, end_iso: str) -> int | None:
    """Calculate duration in ms between two ISO timestamps."""
    try:
        fmt_patterns = ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S%z"]
        start_dt = end_dt = None
        for fmt in fmt_patterns:
            try:
                start_dt = datetime.strptime(start_iso, fmt)
                break
            except ValueError:
                continue
        for fmt in fmt_patterns:
            try:
                end_dt = datetime.strptime(end_iso, fmt)
                break
            except ValueError:
                continue
        if start_dt and end_dt:
            return max(0, int((end_dt - start_dt).total_seconds() * 1000))
    except Exception as exc:
        logger.warning("Suppressed exception: %s", exc)
    return None


def process_transcript(file_path: str, telemetry: CortexTelemetry):
    """Process a single transcript.jsonl with positional correlation."""
    session_id = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(file_path))))
    with open(file_path) as f:
        lines = f.readlines()
    steps = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            steps.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    i = 0
    events_emitted = 0
    while i < len(steps):
        step = steps[i]
        tool_calls = step.get("tool_calls")
        if not tool_calls:
            i += 1
            continue
        planner_step_idx = step.get("step_index", i)
        planner_created_at = step.get("created_at", "")
        for j, call in enumerate(tool_calls):
            tool_name = call.get("name", "")
            tool_args = call.get("args", {})
            info = _extract_skill_info(tool_name, tool_args)
            call_id = f"{session_id}_{planner_step_idx}_{j}"
            telemetry.log_event(
                session_id=session_id,
                call_id=call_id,
                skill=info["skill"],
                source=info["source"],
                event_type="tool_start",
                trigger="desktop_app",
            )
            events_emitted += 1
            result_idx = i + 1 + j
            if result_idx < len(steps):
                result_step = steps[result_idx]
                result_content = result_step.get("content", "")
                result_status = result_step.get("status", "")
                created_at = _parse_timestamp(result_content) or planner_created_at
                completed_at = _parse_completed_at(result_content)
                duration = None
                if created_at and completed_at:
                    duration = _duration_ms(created_at, completed_at)
                success = result_status == "DONE"
                telemetry.log_event(
                    session_id=session_id,
                    call_id=call_id,
                    skill=info["skill"],
                    source=info["source"],
                    event_type="tool_end",
                    trigger="desktop_app",
                    duration_ms=duration,
                    success=success,
                )
                events_emitted += 1
        i += 1 + len(tool_calls)
    return events_emitted


def parse_iso(ts):
    """PENDING: Document parse_iso"""
    if not ts:
        return None
    for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S%z"]:
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return None


def _load_workflow_metadata() -> dict[str, int]:
    """Load expected duration for workflows from metadata."""
    workflow_meta = {}
    wf_dir = "/Users/borjafernandezangulo/.agents/workflows"
    if os.path.exists(wf_dir):
        files = glob.glob(os.path.join(wf_dir, "*.md"))
        for f in files:
            name = os.path.splitext(os.path.basename(f))[0]
            try:
                with open(f, encoding="utf-8") as fh:
                    content = fh.read()
                match = re.search("expected_duration_min:\\s*(\\d+)", content)
                workflow_meta[name] = int(match.group(1)) if match else 15
            except Exception:
                workflow_meta[name] = 15
    return workflow_meta


def _analyze_steps(
    lines: list[dict[str, Any]], workflow_meta: dict[str, int]
) -> tuple[set[str], set[str], int, int]:
    """Analyze step log lines to find viewed/referenced workflows and counts."""
    viewed_workflows = set()
    referenced_workflows = set()
    non_wf_tool_calls = 0
    artifacts_generated = 0
    for step in lines:
        for call in step.get("tool_calls", []):
            name = call.get("name", "")
            args = call.get("args", {})
            if name == "view_file":
                path = args.get("AbsolutePath", "")
                m = re.search("workflows/([^/]+)\\.md", path)
                if m:
                    viewed_workflows.add(m.group(1))
                    continue
            if name in ["write_to_file", "replace_file_content", "multi_replace_file_content"]:
                if args.get("IsArtifact") or args.get("ArtifactMetadata"):
                    artifacts_generated += 1
            non_wf_tool_calls += 1
        if step.get("source") == "USER_EXPLICIT" or step.get("type") == "USER_INPUT":
            content = step.get("content", "")
            for wf in workflow_meta:
                if re.search("^\\s*/" + re.escape(wf) + "\\b", content, re.MULTILINE):
                    referenced_workflows.add(wf)
    return viewed_workflows, referenced_workflows, non_wf_tool_calls, artifacts_generated


def _compute_funnel_states(
    viewed_workflows: set[str],
    referenced_workflows: set[str],
    non_wf_tool_calls: int,
    artifacts_generated: int,
    success: bool,
) -> dict[str, dict[str, Any]]:
    """Compute states and scores for workflows in a session."""
    session_workflows = {}
    all_wfs = viewed_workflows.union(referenced_workflows)
    for wf in all_wfs:
        state = "VIEWED"
        score = 1.0
        if wf in referenced_workflows:
            state = "REFERENCED"
            score += 2.0
            if non_wf_tool_calls >= 2:
                state = "EXECUTED"
                score += 5.0 + 0.5 * non_wf_tool_calls + 2.0 * artifacts_generated
                if success:
                    state = "COMPLETED"
                    score += 10.0
        session_workflows[wf] = {"state": state, "execution_score": round(score, 2)}
    return session_workflows


def _calculate_session_duration(lines: list[dict[str, Any]]) -> tuple[float, datetime | None]:
    """Calculate actual session duration in minutes and start datetime."""
    start_ts = lines[0].get("created_at")
    end_ts = lines[-1].get("created_at")
    start_raw = _parse_timestamp(lines[0].get("content", "")) or start_ts
    end_raw = _parse_completed_at(lines[-1].get("content", "")) or end_ts
    start_dt = parse_iso(start_raw)
    end_dt = parse_iso(end_raw)
    if not (start_dt and end_dt):
        actual_min = 0.1
    else:
        actual_min = max(0.1, (end_dt - start_dt).total_seconds() / 60.0)
    return actual_min, start_dt


def _parse_outcome_score(lines: list[dict[str, Any]]) -> float:
    """Parse output score from explicit user command '/score'."""
    outcome_score = 1.0
    for step in reversed(lines):
        if step.get("source") == "USER_EXPLICIT" and "/score" in step.get("content", ""):
            m = re.search("/score\\s+([0-9.]+)", step.get("content", ""))
            if m:
                outcome_score = float(m.group(1))
                break
    return outcome_score


def _parse_single_transcript(t: str, workflow_meta: dict[str, int]) -> dict[str, Any] | None:
    """Parse a single transcript and compile its metrics."""
    session_id = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(t))))
    try:
        with open(t, encoding="utf-8") as fh:
            lines = [json.loads(line) for line in fh if line.strip()]
    except Exception:
        return None
    if not lines:
        return None

    (
        viewed_workflows,
        referenced_workflows,
        non_wf_tool_calls,
        artifacts_generated,
    ) = _analyze_steps(lines, workflow_meta)

    all_wfs = viewed_workflows.union(referenced_workflows)
    if not all_wfs:
        return None

    success = lines[-1].get("status") != "ERROR"
    session_workflows = _compute_funnel_states(
        viewed_workflows, referenced_workflows, non_wf_tool_calls, artifacts_generated, success
    )

    actual_min, start_dt = _calculate_session_duration(lines)
    outcome_score = _parse_outcome_score(lines)

    start_ts = lines[0].get("created_at")
    end_ts = lines[-1].get("created_at")

    return {
        "timestamp": end_ts or start_ts,
        "session_id": session_id,
        "workflows": session_workflows,
        "actual_min": actual_min,
        "success": success,
        "start_dt": start_dt or datetime.now(timezone.utc),
        "outcome_score": outcome_score,
        "artifacts": artifacts_generated,
        "tool_calls": non_wf_tool_calls,
    }


def _compute_cronos_records(
    raw_sessions: list[dict[str, Any]],
    workflow_meta: dict[str, int],
    rolling_window: int,
) -> list[dict[str, Any]]:
    """Compute Cronos metrics and exergy scores across raw sessions."""
    import statistics

    cronos_records = []
    history = {}
    for session in raw_sessions:
        for wf, funnel in session["workflows"].items():
            if wf not in history:
                history[wf] = []
            planned = (
                statistics.median(history[wf][-rolling_window:])
                if history[wf]
                else workflow_meta.get(wf, 15)
            )
            actual_min = session["actual_min"]
            outcome_score = session["outcome_score"]
            state = funnel["state"]
            exec_score = funnel["execution_score"]
            if state in ["EXECUTED", "COMPLETED"]:
                deviation = actual_min - planned
                time_saved = planned - actual_min
                exergy_yield = (
                    time_saved * outcome_score
                    if time_saved > 0
                    else time_saved / max(0.1, outcome_score)
                )
                time_exergy_score = outcome_score / actual_min
            else:
                deviation = 0.0
                exergy_yield = 0.0
                time_exergy_score = 0.0
            record = {
                "timestamp": session["timestamp"],
                "session_id": session["session_id"],
                "workflow": wf,
                "state": state,
                "execution_score": exec_score,
                "planned_minutes": round(planned, 2),
                "actual_minutes": round(actual_min, 2),
                "deviation_minutes": round(deviation, 2),
                "outcome_score": outcome_score,
                "exergy_score": round(time_exergy_score, 4),
                "exergy_yield": round(exergy_yield, 2),
                "success": session["success"],
                "artifacts": session["artifacts"],
                "tool_calls": session["tool_calls"],
            }
            cronos_records.append(record)
            if state == "COMPLETED":
                history[wf].append(actual_min)
    return cronos_records


def _compile_stats(cronos_records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Compile viewed, referenced, executed, completed metrics for each workflow."""
    stats = {}
    for r in cronos_records:
        wf = r["workflow"]
        if wf not in stats:
            stats[wf] = {
                "viewed": 0,
                "referenced": 0,
                "executed": 0,
                "completed": 0,
                "planned_sum": 0,
                "actual_sum": 0,
                "exergy_sum": 0,
                "exec_score_sum": 0,
            }
        st = r["state"]
        stats[wf]["viewed"] += 1
        if st in ["REFERENCED", "EXECUTED", "COMPLETED"]:
            stats[wf]["referenced"] += 1
        if st in ["EXECUTED", "COMPLETED"]:
            stats[wf]["executed"] += 1
            stats[wf]["planned_sum"] += r["planned_minutes"]
            stats[wf]["actual_sum"] += r["actual_minutes"]
            stats[wf]["exergy_sum"] += r["exergy_yield"]
        if st == "COMPLETED":
            stats[wf]["completed"] += 1
        stats[wf]["exec_score_sum"] += r["execution_score"]
    return stats


def _write_cronos_report(stats: dict[str, dict[str, Any]], report_path: str) -> None:
    """Generate and write the markdown report."""
    report_lines = [
        "# CRONOS v0.2 — Execution Funnel & Exergy Report",
        f"> **Reality Level: C5-REAL** | Compiled: {datetime.now(timezone.utc).isoformat()}Z",
        "",
        "## Workflow Observability Funnel",
        "State transitions tracking real execution vs mere references.",
        "",
        "| Workflow | Viewed | Referenced | Executed | Completed | Drop-off | Avg Exec Score |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for wf, s in sorted(stats.items(), key=lambda x: x[1]["executed"], reverse=True):
        if s["viewed"] == 0:
            continue
        drop_off = f"{(1 - s['completed'] / s['viewed']) * 100:.1f}%"
        avg_score = s["exec_score_sum"] / s["viewed"]
        report_lines.append(
            f"| `{wf}` | {s['viewed']} | {s['referenced']} | {s['executed']} | {s['completed']} | {drop_off} | {avg_score:.1f} |"
        )
    report_lines.extend(
        [
            "",
            "## Exergy Analytics (Executed Only)",
            "Positive exergy yield indicates time saved relative to plan; negative exergy yield identifies workflow friction.",
            "",
            "| Workflow | Runs | Avg Planned | Avg Actual | Avg Deviation | Total Exergy Yield | Success Rate |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )
    sorted_exergy = sorted(stats.items(), key=lambda x: x[1]["exergy_sum"], reverse=True)
    for wf, s in sorted_exergy:
        runs = s["executed"]
        if runs == 0:
            continue
        avg_planned = s["planned_sum"] / runs
        avg_actual = s["actual_sum"] / runs
        avg_dev = (s["actual_sum"] - s["planned_sum"]) / runs
        total_exergy = s["exergy_sum"]
        success_rate = s["completed"] / runs * 100
        report_lines.append(
            f"| `{wf}` | {runs} | {avg_planned:.1f}m | {avg_actual:.1f}m | {avg_dev:+.1f}m | {total_exergy:+.1f}m | {success_rate:.1f}% |"
        )
    report_content = "\n".join(report_lines)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report_content)


def run_cronos_analysis(transcripts, rolling_window=5) -> None:
    """
    Parses workflow metadata and evaluates session durations to construct
    operational memory (CRONOS v0) and exergy rankings.
    Implements Execution Funnel (VIEWED -> REFERENCED -> EXECUTED -> COMPLETED).
    """
    CRONOS_LOG = os.path.expanduser("~/.gemini/config/skills/_metrics/cronos_memory.jsonl")
    CRONOS_REPORT = os.path.expanduser("~/.gemini/config/skills/_metrics/cronos_report.md")

    workflow_meta = _load_workflow_metadata()
    raw_sessions = []
    for t in transcripts:
        session = _parse_single_transcript(t, workflow_meta)
        if session:
            raw_sessions.append(session)

    raw_sessions.sort(key=lambda x: x["start_dt"])
    cronos_records = _compute_cronos_records(raw_sessions, workflow_meta, rolling_window)

    os.makedirs(os.path.dirname(CRONOS_LOG), exist_ok=True)
    with open(CRONOS_LOG, "w", encoding="utf-8") as fh:
        for r in cronos_records:
            fh.write(json.dumps(r) + "\n")

    stats = _compile_stats(cronos_records)
    _write_cronos_report(stats, CRONOS_REPORT)
    logger.info(f"Generated CRONOS report in {CRONOS_REPORT}")


def ingest_all_transcripts(log_path: str = LOG_FILE):
    """Ingest all transcripts from the brain directory."""
    if os.path.exists(log_path):
        os.remove(log_path)
    telemetry = CortexTelemetry(log_path=log_path)
    base_dir = os.path.expanduser("~/.gemini/antigravity/brain")
    transcripts = glob.glob(f"{base_dir}/*/.system_generated/logs/transcript.jsonl")
    total_events = 0
    processed = 0
    sorted_transcripts = sorted(transcripts)
    for t in sorted_transcripts:
        try:
            n = process_transcript(t, telemetry)
            total_events += n
            processed += 1
        except Exception as e:
            logger.info(f"  ERROR processing {t}: {e}")
    logger.info(f"Processed {processed}/{len(transcripts)} transcripts → {total_events} events")
    run_cronos_analysis(sorted_transcripts)
    return total_events


if __name__ == "__main__":
    ingest_all_transcripts()
