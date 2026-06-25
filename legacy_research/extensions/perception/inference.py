# [C5-REAL] Exergy-Maximized
"""
Perception Layer 2: Behavioral Inference.

Rule-based intent inference from file activity statistics.
"""

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from legacy_research.extensions.perception.base import (
    MIN_EVENTS_FOR_INFERENCE,
    BehavioralSnapshot,
    FileEvent,
)
from legacy_research.memory.temporal import now_iso

__all__ = ["compute_event_stats", "infer_behavior"]
_INTENT_RULES: list[tuple[Callable[[dict], bool], str, str, str]] = []


def _rule(intent: str, emotion: str, confidence: str):
    """Decorator to register an intent inference rule."""

    def decorator(fn: Callable[[dict], bool]):
        """PENDING: Document decorator"""
        _INTENT_RULES.append((fn, intent, emotion, confidence))
        return fn

    return decorator


def compute_event_stats(events: list[FileEvent]) -> dict:
    """Compute statistical features from a window of events."""
    if not events:
        return {"total": 0}
    total = len(events)
    roles = defaultdict(int)
    event_types = defaultdict(int)
    dirs = defaultdict(int)
    files = defaultdict(int)
    for e in events:
        roles[e.role] += 1
        event_types[e.event_type] += 1
        dirs[str(Path(e.path).parent)] += 1
        files[e.path] += 1
    max_dir_count = max(dirs.values()) if dirs else 0
    max_file_count = max(files.values()) if files else 0
    source_modified = sum(1 for e in events if e.role == "source" and e.event_type == "modified")
    return {
        "total": total,
        "test_ratio": roles.get("test", 0) / total,
        "config_ratio": roles.get("config", 0) / total,
        "docs_ratio": roles.get("docs", 0) / total,
        "source_ratio": roles.get("source", 0) / total,
        "create_ratio": event_types.get("created", 0) / total,
        "delete_ratio": event_types.get("deleted", 0) / total,
        "modify_ratio": event_types.get("modified", 0) / total,
        "max_dir_ratio": max_dir_count / total,
        "max_file_ratio": max_file_count / total,
        "source_modified": source_modified,
        "unique_files": len(files),
        "unique_dirs": len(dirs),
    }


def infer_behavior(events: list[FileEvent]) -> BehavioralSnapshot:
    """Infer user behavior from a window of file events.

    Evaluates all intent rules against computed statistics.
    The first matching rule wins (rules are ordered by specificity).
    """
    stats = compute_event_stats(events)
    total = stats.get("total", 0)
    if total < MIN_EVENTS_FOR_INFERENCE:
        return BehavioralSnapshot(
            intent="unknown",
            emotion="neutral",
            confidence="C1",
            project=_dominant_project(events),
            event_count=total,
            window_seconds=_window_duration(events),
            top_files=_top_files(events, 5),
            summary=f"Insufficient activity ({total} events)",
            timestamp=now_iso(),
        )
    for condition, intent, emotion, confidence in _INTENT_RULES:
        if condition(stats):
            project = _dominant_project(events)
            return BehavioralSnapshot(
                intent=intent,
                emotion=emotion,
                confidence=confidence,
                project=project,
                event_count=total,
                window_seconds=_window_duration(events),
                top_files=_top_files(events, 5),
                summary=_generate_summary(intent, emotion, total, project),
                timestamp=now_iso(),
            )
    return BehavioralSnapshot(
        intent="active",
        emotion="neutral",
        confidence="C2",
        project=_dominant_project(events),
        event_count=total,
        window_seconds=_window_duration(events),
        top_files=_top_files(events, 5),
        summary=f"General activity: {total} file events",
        timestamp=now_iso(),
    )


def _dominant_project(events: list[FileEvent]) -> str | None:
    """Find the most common project in an event list."""
    projects = defaultdict(int)
    for e in events:
        if e.project:
            projects[e.project] += 1
    if not projects:
        return None
    return max(projects, key=projects.get)  # pyright: ignore[reportArgumentType,reportCallIssue]


def _window_duration(events: list[FileEvent]) -> float:
    """Duration of the event window in seconds."""
    if len(events) < 2:
        return 0.0
    return events[-1].timestamp - events[0].timestamp


def _top_files(events: list[FileEvent], n: int) -> list[str]:
    """Most frequently touched files."""
    counts: dict[str, int] = defaultdict(int)
    for e in events:
        counts[Path(e.path).name] += 1
    return [f for f, _ in sorted(counts.items(), key=lambda x: -x[1])[:n]]


def _generate_summary(intent: str, emotion: str, count: int, project: str | None) -> str:
    """Generate a human-readable summary."""
    intents = {
        "debugging": "Debugging/testing session detected",
        "setup": "Infrastructure/configuration work",
        "deep_work": "Focused deep work session",
        "experimenting": "Experimentation cycle (create-delete-iterate)",
        "frustrated_iteration": "Iterating on same file repeatedly (possibly stuck)",
        "documenting": "Documentation pass",
        "refactoring": "Multi-file refactoring session",
    }
    desc = intents.get(intent, f"Activity: {intent}")
    proj = f" on {project}" if project else ""
    return f"{desc}{proj} ({count} events, emotion: {emotion})"
