"""
CORTEX v4.0 — Real-Time Perception Engine.

Three-layer behavioral perception:
  1. FileActivityObserver — watches workspace via watchdog FSEvents
  2. BehavioralInference — infers intent from activity patterns
  3. PerceptionRecorder — auto-records episodes when confidence is high

Runs as a background observer, feeding the Episodic Memory system
with automatically-detected behavioral events.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from cortex.episodic import EpisodicMemory
from cortex.temporal import now_iso

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.perception")


# ─── Constants ───────────────────────────────────────────────────────

DEBOUNCE_SECONDS = 2.0
INFERENCE_WINDOW_SECONDS = 300  # 5 minutes
RECORD_COOLDOWN_SECONDS = 300  # 1 episode per 5min per project
MIN_EVENTS_FOR_INFERENCE = 3  # need at least 3 events to infer

# File classification patterns
_FILE_ROLES: list[tuple[str, re.Pattern]] = [
    ("test", re.compile(r"(test_|_test\.|spec\.|\.test\.)", re.IGNORECASE)),
    (
        "config",
        re.compile(
            r"(\.env|config\.|settings\.|\.toml|\.ini|\.ya?ml|Makefile|Dockerfile|(?:\.json$))",
            re.IGNORECASE,
        ),
    ),
    ("docs", re.compile(r"(\.md$|\.rst$|\.txt$|README|CHANGELOG|docs/)", re.IGNORECASE)),
    ("asset", re.compile(r"\.(png|jpg|svg|ico|woff|ttf|mp3|mp4|webp)$", re.IGNORECASE)),
    ("source", re.compile(r"\.(py|ts|tsx|js|jsx|swift|rs|go|css|html)$", re.IGNORECASE)),
]

# Git/hidden paths to always ignore
_IGNORE_PATTERNS = re.compile(
    r"(\.git/|__pycache__|\.pyc$|node_modules/|\.DS_Store|\.venv/|\.pytest_cache)"
)


# ─── Data Models ─────────────────────────────────────────────────────


@dataclass
class FileEvent:
    """A single file system event after debouncing."""

    path: str
    event_type: str  # created, modified, deleted, moved
    role: str  # test, config, docs, asset, source, unknown
    project: str | None
    timestamp: float

    @property
    def basename(self) -> str:
        return Path(self.path).name


@dataclass
class BehavioralSnapshot:
    """Inferred user behavior from a window of file events."""

    intent: str  # debugging, deep_work, refactoring, setup, experimenting, documenting, unknown
    emotion: str  # frustrated, flow, curious, cautious, confident, neutral
    confidence: str  # C1-C5
    project: str | None
    event_count: int
    window_seconds: float
    top_files: list[str]
    summary: str
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "emotion": self.emotion,
            "confidence": self.confidence,
            "project": self.project,
            "event_count": self.event_count,
            "window_seconds": round(self.window_seconds, 1),
            "top_files": self.top_files[:5],
            "summary": self.summary,
            "timestamp": self.timestamp,
        }


# ─── Layer 1: File Activity Observer ─────────────────────────────────


def classify_file(path: str) -> str:
    """Classify a file path into a role category."""
    for role, pattern in _FILE_ROLES:
        if pattern.search(path):
            return role
    return "unknown"


def infer_project_from_path(path: str, workspace_root: str | None = None) -> str | None:
    """Infer project name from file path.

    Tries to extract the project directory name from the path,
    using workspace_root as reference if provided.
    """
    p = Path(path)

    if workspace_root:
        root = Path(workspace_root)
        try:
            rel = p.relative_to(root)
            parts = rel.parts
            if parts:
                return parts[0] if len(parts) > 1 else root.name
        except ValueError:
            pass

    # Fallback: use parent directory name
    if p.parent.name and p.parent.name not in (".", "/"):
        return p.parent.name

    return None


def should_ignore(path: str) -> bool:
    """Check if a path should be ignored."""
    return bool(_IGNORE_PATTERNS.search(path))


class _DebouncedHandler(FileSystemEventHandler):
    """Watchdog handler with debouncing for rapid file changes."""

    def __init__(
        self,
        callback: Callable[[FileEvent], None],
        workspace: str,
        debounce_s: float = DEBOUNCE_SECONDS,
    ) -> None:
        super().__init__()
        self.callback = callback
        self.workspace = workspace
        self.debounce_s = debounce_s
        self._last_events: dict[str, float] = {}

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        path = str(event.src_path)
        if should_ignore(path):
            return

        now = time.monotonic()
        last = self._last_events.get(path, 0)
        if now - last < self.debounce_s:
            return  # debounced

        self._last_events[path] = now

        # Classify
        ev_type = (
            event.event_type
            if event.event_type in {"created", "modified", "deleted", "moved"}
            else "modified"
        )
        role = classify_file(path)
        project = infer_project_from_path(path, self.workspace)

        fe = FileEvent(
            path=path,
            event_type=ev_type,
            role=role,
            project=project,
            timestamp=now,
        )
        self.callback(fe)

    def cleanup_old_entries(self, max_age: float = 600) -> None:
        """Remove old debounce entries to prevent memory leak."""
        now = time.monotonic()
        expired = [k for k, v in self._last_events.items() if now - v > max_age]
        for k in expired:
            del self._last_events[k]


class FileActivityObserver:
    """Watches a workspace directory for file changes via FSEvents.

    Usage:
        observer = FileActivityObserver("/path/to/workspace")
        observer.start()
        # ... events flow to the callback
        observer.stop()
    """

    def __init__(
        self,
        workspace: str,
        callback: Callable[[FileEvent], None],
        debounce_s: float = DEBOUNCE_SECONDS,
        recursive: bool = True,
    ) -> None:
        self.workspace = workspace
        self.handler = _DebouncedHandler(callback, workspace, debounce_s)
        self._observer = Observer()
        self._observer.schedule(self.handler, workspace, recursive=recursive)

    def start(self) -> None:
        """Start watching the filesystem."""
        self._observer.start()
        logger.info("FileActivityObserver started: %s", self.workspace)

    def stop(self) -> None:
        """Stop watching the filesystem."""
        self._observer.stop()
        self._observer.join(timeout=5)
        logger.info("FileActivityObserver stopped")

    @property
    def is_alive(self) -> bool:
        return self._observer.is_alive()


# ─── Layer 2: Behavioral Inference ───────────────────────────────────


# Intent inference rules: (condition_fn, intent, emotion, confidence)
_INTENT_RULES: list[tuple[Callable[[dict], bool], str, str, str]] = []


def _rule(intent: str, emotion: str, confidence: str):
    """Decorator to register an intent inference rule."""

    def decorator(fn: Callable[[dict], bool]):
        _INTENT_RULES.append((fn, intent, emotion, confidence))
        return fn

    return decorator


@_rule("debugging", "cautious", "C4")
def _test_heavy(stats: dict) -> bool:
    """Tests being modified/created > 40% of events."""
    return stats.get("test_ratio", 0) > 0.4


@_rule("setup", "neutral", "C3")
def _config_heavy(stats: dict) -> bool:
    """Config files dominate activity."""
    return stats.get("config_ratio", 0) > 0.5


@_rule("frustrated_iteration", "frustrated", "C4")
def _same_file_repeated(stats: dict) -> bool:
    """Same file saved many times = stuck."""
    return stats.get("max_file_ratio", 0) > 0.5 and stats.get("total", 0) >= 5


@_rule("deep_work", "flow", "C4")
def _single_dir_focused(stats: dict) -> bool:
    """Many files in a single directory = deep focused work."""
    return stats.get("max_dir_ratio", 0) > 0.7 and stats.get("total", 0) >= 5


@_rule("experimenting", "curious", "C3")
def _rapid_create_delete(stats: dict) -> bool:
    """Rapid create-delete cycles = experimentation."""
    return stats.get("delete_ratio", 0) > 0.3 and stats.get("create_ratio", 0) > 0.2


@_rule("documenting", "confident", "C3")
def _docs_heavy(stats: dict) -> bool:
    """Documentation files dominate."""
    return stats.get("docs_ratio", 0) > 0.5


@_rule("refactoring", "flow", "C3")
def _multi_source_edits(stats: dict) -> bool:
    """Many source files being modified = refactoring."""
    source_modified = stats.get("source_modified", 0)
    return source_modified >= 4 and stats.get("source_ratio", 0) > 0.6


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

    # Evaluate rules
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

    # Default: generic activity
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
    return max(projects, key=projects.get)


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


# ─── Layer 3: Perception Recorder ───────────────────────────────────


class PerceptionRecorder:
    """Auto-records behavioral snapshots to episodic memory.

    Rate-limited to avoid overwhelming the episode store.
    Only records when inference confidence >= C3.
    """

    MIN_CONFIDENCE = {"C3", "C4", "C5"}

    def __init__(
        self,
        conn: aiosqlite.Connection,
        session_id: str,
        cooldown_s: float = RECORD_COOLDOWN_SECONDS,
    ) -> None:
        self.memory = EpisodicMemory(conn)
        self.session_id = session_id
        self.cooldown_s = cooldown_s
        self._last_record: dict[str, float] = {}  # project -> timestamp

    async def maybe_record(self, snapshot: BehavioralSnapshot) -> int | None:
        """Record a snapshot if confidence is high enough and cooldown has passed.

        Returns:
            Episode ID if recorded, None if skipped.
        """
        if snapshot.confidence not in self.MIN_CONFIDENCE:
            return None

        # Rate limit per project
        project_key = snapshot.project or "__global__"
        now = time.monotonic()
        last = self._last_record.get(project_key, 0)
        if now - last < self.cooldown_s:
            return None

        self._last_record[project_key] = now

        # Map intent to episodic event type
        event_type_map = {
            "debugging": "discovery",
            "setup": "decision",
            "deep_work": "flow_state",
            "experimenting": "discovery",
            "frustrated_iteration": "blocked",
            "documenting": "milestone",
            "refactoring": "decision",
        }
        event_type = event_type_map.get(snapshot.intent, "insight")

        episode_id = await self.memory.record(
            session_id=self.session_id,
            event_type=event_type,
            content=snapshot.summary,
            project=snapshot.project,
            emotion=snapshot.emotion,
            tags=["auto-perceived", "behavioral"],
            meta=snapshot.to_dict(),
        )

        logger.info(
            "Auto-recorded episode #%d: %s (%s)",
            episode_id,
            snapshot.intent,
            snapshot.confidence,
        )
        return episode_id


# ─── Full Perception Pipeline ────────────────────────────────────────


class PerceptionPipeline:
    """Complete perception pipeline combining all 3 layers.

    Usage:
        pipeline = PerceptionPipeline(conn, session_id, workspace)
        pipeline.start()
        # ... runs in background, auto-records episodes
        pipeline.stop()
    """

    def __init__(
        self,
        conn: aiosqlite.Connection,
        session_id: str,
        workspace: str,
        window_s: float = INFERENCE_WINDOW_SECONDS,
        cooldown_s: float = RECORD_COOLDOWN_SECONDS,
    ) -> None:
        self.workspace = workspace
        self.window_s = window_s
        self._events: list[FileEvent] = []
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

        self.recorder = PerceptionRecorder(conn, session_id, cooldown_s)
        self.observer = FileActivityObserver(
            workspace=workspace,
            callback=self._on_event,
        )

    def _on_event(self, event: FileEvent) -> None:
        """Callback from the watchdog thread — thread-safe append."""
        self._events.append(event)

    def start(self) -> None:
        """Start the observer."""
        self.observer.start()
        logger.info("PerceptionPipeline started: %s", self.workspace)

    def stop(self) -> None:
        """Stop the observer."""
        self.observer.stop()
        logger.info("PerceptionPipeline stopped")

    @property
    def is_alive(self) -> bool:
        return self.observer.is_alive

    def get_window_events(self) -> list[FileEvent]:
        """Get events within the current inference window."""
        now = time.monotonic()
        cutoff = now - self.window_s
        # Prune old events
        self._events = [e for e in self._events if e.timestamp >= cutoff]
        return list(self._events)

    async def tick(self) -> BehavioralSnapshot | None:
        """Run one inference cycle.

        Call this periodically (e.g. every 30s) to process accumulated events.

        Returns:
            BehavioralSnapshot if inference was made, None if insufficient data.
        """
        events = self.get_window_events()
        if len(events) < MIN_EVENTS_FOR_INFERENCE:
            return None

        snapshot = infer_behavior(events)
        await self.recorder.maybe_record(snapshot)
        return snapshot

    @property
    def event_count(self) -> int:
        return len(self._events)
