"""Continuity Monitor — Cognitive Persistence Layer.

Solves the fundamental AI agent limitation: cognition compression per invocation.
This monitor runs every 5 minutes via the daemon, observes system state, and
persists a structured temporal log that any future AI invocation can consume
to reconstruct full cognitive continuity over arbitrary time windows (8h+).

The monitor tracks:
- File system mutations (git commits, file changes)
- CORTEX fact creation/modification
- Process activity (dev servers, builds)
- Ghost state evolution
- Decision/error patterns across time

Output: ~/.cortex/continuity/timeline.jsonl  (append-only temporal log)
        ~/.cortex/continuity/briefing.md     (condensed human/AI-readable briefing)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("moskv-daemon.continuity")

CONTINUITY_DIR = Path.home() / ".cortex" / "continuity"
TIMELINE_FILE = CONTINUITY_DIR / "timeline.jsonl"
BRIEFING_FILE = CONTINUITY_DIR / "briefing.md"
STATE_FILE = CONTINUITY_DIR / "state.json"

# Maximum timeline entries to keep (roughly 24h at 5min intervals = 288 entries)
MAX_TIMELINE_ENTRIES = 500


@dataclass
class ContinuityEvent:
    """A single point-in-time observation of system state."""

    timestamp: str
    epoch: float
    event_type: str  # git_commit, fact_created, file_changed, process_active, ghost_change
    project: str = ""
    summary: str = ""
    detail: str = ""
    importance: int = 1  # 1-5 scale


@dataclass
class ContinuityAlert:
    """Alert for continuity gaps or significant state changes."""

    issue: str
    detail: str = ""


@dataclass
class ContinuityState:
    """Persisted state between continuity checks for delta detection."""

    last_git_hashes: dict[str, str] = field(default_factory=dict)  # project -> last_commit
    last_fact_count: int = 0
    last_check_epoch: float = 0.0
    active_processes: list[str] = field(default_factory=list)


class ContinuityMonitor:
    """Daemon monitor that maintains cognitive continuity across AI invocations.

    Every check cycle (5min), it captures:
    1. Git activity across all known repos
    2. CORTEX database mutations
    3. Active development processes
    4. File system changes in watched directories
    5. Ghost state transitions

    Results are persisted to an append-only JSONL timeline and a condensed
    briefing file that any AI invocation can read at startup.
    """

    def __init__(
        self,
        db_path: Path | None = None,
        watched_dirs: list[str] | None = None,
        briefing_hours: float = 8.0,
    ):
        self.db_path = db_path or (Path.home() / ".cortex" / "cortex.db")
        self.watched_dirs = watched_dirs or [str(Path.home() / "cortex")]
        self.briefing_hours = briefing_hours
        self._state = self._load_state()
        CONTINUITY_DIR.mkdir(parents=True, exist_ok=True)

    def check(self) -> list[ContinuityAlert]:
        """Run continuity check — captures system state delta."""
        alerts: list[ContinuityAlert] = []
        events: list[ContinuityEvent] = []
        now = datetime.now(timezone.utc)
        epoch = time.time()

        # 1. Git activity
        git_events = self._scan_git_activity(now)
        events.extend(git_events)

        # 2. CORTEX fact mutations
        fact_events = self._scan_cortex_facts(now)
        events.extend(fact_events)

        # 3. Active processes
        proc_events = self._scan_processes(now)
        events.extend(proc_events)

        # 4. File system pulse
        fs_events = self._scan_filesystem_pulse(now)
        events.extend(fs_events)

        # Persist events to timeline
        if events:
            self._append_timeline(events)

        # Detect continuity gaps
        if self._state.last_check_epoch > 0:
            gap_hours = (epoch - self._state.last_check_epoch) / 3600
            if gap_hours > 1.0:
                alerts.append(
                    ContinuityAlert(
                        issue="continuity_gap",
                        detail=f"Daemon was offline for {gap_hours:.1f}h. "
                        f"Gap: {datetime.fromtimestamp(self._state.last_check_epoch, tz=timezone.utc).isoformat()} → {now.isoformat()}",
                    )
                )

        # Update state
        self._state.last_check_epoch = epoch
        self._save_state()

        # Regenerate briefing
        self._generate_briefing()

        # Prune old timeline entries
        self._prune_timeline()

        logger.info(
            "⏳ Continuity: %d events captured, %d alerts",
            len(events),
            len(alerts),
        )
        return alerts

    # ─── Scanners ──────────────────────────────────────────────────

    def _scan_git_activity(self, now: datetime) -> list[ContinuityEvent]:
        """Scan all watched dirs for new git commits since last check."""
        events: list[ContinuityEvent] = []

        for watch_dir in self.watched_dirs:
            watch_path = Path(watch_dir)
            if not watch_path.exists():
                continue

            # Find git repos (max depth 2)
            try:
                result = subprocess.run(
                    ["find", str(watch_path), "-maxdepth", "3", "-name", ".git", "-type", "d"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                git_dirs = [Path(p).parent for p in result.stdout.strip().split("\n") if p]
            except (subprocess.TimeoutExpired, OSError):
                continue

            for repo_dir in git_dirs:
                project = repo_dir.name
                try:
                    # Get latest commit hash
                    result = subprocess.run(
                        ["git", "log", "--oneline", "-1", "--format=%H|%s|%ai"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        cwd=str(repo_dir),
                    )
                    if result.returncode != 0 or not result.stdout.strip():
                        continue

                    parts = result.stdout.strip().split("|", 2)
                    if len(parts) < 3:
                        continue

                    current_hash = parts[0]
                    commit_msg = parts[1]
                    commit_date = parts[2]

                    prev_hash = self._state.last_git_hashes.get(project, "")

                    if prev_hash and current_hash != prev_hash:
                        # Count commits since last check
                        count_result = subprocess.run(
                            ["git", "rev-list", "--count", f"{prev_hash}..{current_hash}"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                            cwd=str(repo_dir),
                        )
                        count = int(count_result.stdout.strip()) if count_result.returncode == 0 else 1

                        # Get changed files summary
                        diff_result = subprocess.run(
                            ["git", "diff", "--stat", f"{prev_hash}..{current_hash}"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                            cwd=str(repo_dir),
                        )
                        stat_summary = diff_result.stdout.strip().split("\n")[-1] if diff_result.stdout.strip() else ""

                        events.append(
                            ContinuityEvent(
                                timestamp=now.isoformat(),
                                epoch=time.time(),
                                event_type="git_commit",
                                project=project,
                                summary=f"{count} new commit(s): {commit_msg}",
                                detail=stat_summary,
                                importance=min(3 + count, 5),
                            )
                        )
                    elif not prev_hash:
                        # First time seeing this repo — record baseline
                        events.append(
                            ContinuityEvent(
                                timestamp=now.isoformat(),
                                epoch=time.time(),
                                event_type="git_baseline",
                                project=project,
                                summary=f"Baseline: {commit_msg}",
                                detail=commit_date,
                                importance=1,
                            )
                        )

                    self._state.last_git_hashes[project] = current_hash

                except (subprocess.TimeoutExpired, OSError, ValueError):
                    continue

        return events

    def _scan_cortex_facts(self, now: datetime) -> list[ContinuityEvent]:
        """Check CORTEX DB for new facts since last check."""
        events: list[ContinuityEvent] = []
        if not self.db_path.exists():
            return events

        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5)
            conn.row_factory = sqlite3.Row

            # Count total facts
            cursor = conn.execute("SELECT COUNT(*) as cnt FROM facts")
            current_count = cursor.fetchone()["cnt"]

            if self._state.last_fact_count > 0 and current_count > self._state.last_fact_count:
                delta = current_count - self._state.last_fact_count

                # Get the newest facts
                recent = conn.execute(
                    "SELECT type, project, created_at FROM facts ORDER BY id DESC LIMIT ?",
                    (delta,),
                ).fetchall()

                # Group by type for summary
                type_counts: dict[str, int] = {}
                projects_touched: set[str] = set()
                for row in recent:
                    fact_type = row["type"]
                    type_counts[fact_type] = type_counts.get(fact_type, 0) + 1
                    if row["project"]:
                        projects_touched.add(row["project"])

                type_summary = ", ".join(f"{v} {k}" for k, v in sorted(type_counts.items()))
                proj_summary = ", ".join(sorted(projects_touched)) if projects_touched else "global"

                events.append(
                    ContinuityEvent(
                        timestamp=now.isoformat(),
                        epoch=time.time(),
                        event_type="fact_created",
                        project=proj_summary,
                        summary=f"+{delta} facts: {type_summary}",
                        detail=f"Total facts: {current_count}",
                        importance=min(2 + delta // 5, 5),
                    )
                )

            self._state.last_fact_count = current_count
            conn.close()

        except sqlite3.Error as e:
            logger.debug("Continuity DB scan error: %s", e)

        return events

    def _scan_processes(self, now: datetime) -> list[ContinuityEvent]:
        """Detect active development processes (dev servers, builds, tests)."""
        events: list[ContinuityEvent] = []
        dev_patterns = [
            ("vite", "Vite dev server"),
            ("next-server", "Next.js dev server"),
            ("npm run", "npm script"),
            ("pytest", "pytest runner"),
            ("python -m cortex", "CORTEX CLI"),
            ("swift build", "Swift build"),
            ("xcodebuild", "Xcode build"),
        ]

        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = result.stdout.strip().split("\n")

            active_now: list[str] = []
            for line in lines:
                for pattern, label in dev_patterns:
                    if pattern in line.lower():
                        active_now.append(label)
                        break

            active_set = set(active_now)
            prev_set = set(self._state.active_processes)

            # Detect new processes
            started = active_set - prev_set
            stopped = prev_set - active_set

            for proc in started:
                events.append(
                    ContinuityEvent(
                        timestamp=now.isoformat(),
                        epoch=time.time(),
                        event_type="process_started",
                        summary=f"Started: {proc}",
                        importance=2,
                    )
                )

            for proc in stopped:
                events.append(
                    ContinuityEvent(
                        timestamp=now.isoformat(),
                        epoch=time.time(),
                        event_type="process_stopped",
                        summary=f"Stopped: {proc}",
                        importance=2,
                    )
                )

            self._state.active_processes = list(active_set)

        except (subprocess.TimeoutExpired, OSError):
            pass

        return events

    def _scan_filesystem_pulse(self, now: datetime) -> list[ContinuityEvent]:
        """Detect recently modified files in watched directories."""
        events: list[ContinuityEvent] = []

        for watch_dir in self.watched_dirs:
            watch_path = Path(watch_dir)
            if not watch_path.exists():
                continue

            try:
                # Files modified in the last 6 minutes (slightly more than check interval)
                result = subprocess.run(
                    [
                        "find", str(watch_path),
                        "-maxdepth", "3",
                        "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx",
                        "-o", "-name", "*.js", "-o", "-name", "*.jsx",
                        "-o", "-name", "*.swift", "-o", "-name", "*.css",
                        "-o", "-name", "*.html",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                # Filter to recently modified
                recent_files: list[str] = []
                cutoff = time.time() - 360  # 6 minutes ago
                for fpath in result.stdout.strip().split("\n"):
                    if not fpath or "node_modules" in fpath or ".venv" in fpath or "__pycache__" in fpath:
                        continue
                    try:
                        if os.path.getmtime(fpath) > cutoff:
                            recent_files.append(fpath)
                    except OSError:
                        continue

                if recent_files:
                    # Group by extension
                    ext_counts: dict[str, int] = {}
                    for f in recent_files:
                        ext = Path(f).suffix or "other"
                        ext_counts[ext] = ext_counts.get(ext, 0) + 1

                    ext_summary = ", ".join(f"{v}{k}" for k, v in sorted(ext_counts.items()))

                    events.append(
                        ContinuityEvent(
                            timestamp=now.isoformat(),
                            epoch=time.time(),
                            event_type="file_activity",
                            summary=f"{len(recent_files)} files modified: {ext_summary}",
                            detail="\n".join(recent_files[:10]),
                            importance=min(1 + len(recent_files) // 3, 4),
                        )
                    )

            except (subprocess.TimeoutExpired, OSError):
                continue

        return events

    # ─── Persistence ───────────────────────────────────────────────

    def _append_timeline(self, events: list[ContinuityEvent]) -> None:
        """Append events to the JSONL timeline file."""
        try:
            with open(TIMELINE_FILE, "a") as f:
                for event in events:
                    f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error("Failed to write timeline: %s", e)

    def _prune_timeline(self) -> None:
        """Keep timeline within MAX_TIMELINE_ENTRIES limit."""
        if not TIMELINE_FILE.exists():
            return
        try:
            with open(TIMELINE_FILE) as f:
                lines = f.readlines()
            if len(lines) > MAX_TIMELINE_ENTRIES:
                # Keep last N entries
                with open(TIMELINE_FILE, "w") as f:
                    f.writelines(lines[-MAX_TIMELINE_ENTRIES:])
                logger.info("Continuity timeline pruned: %d → %d entries", len(lines), MAX_TIMELINE_ENTRIES)
        except OSError as e:
            logger.error("Failed to prune timeline: %s", e)

    def _load_state(self) -> ContinuityState:
        """Load persisted state from disk."""
        if not STATE_FILE.exists():
            return ContinuityState()
        try:
            data = json.loads(STATE_FILE.read_text())
            return ContinuityState(
                last_git_hashes=data.get("last_git_hashes", {}),
                last_fact_count=data.get("last_fact_count", 0),
                last_check_epoch=data.get("last_check_epoch", 0.0),
                active_processes=data.get("active_processes", []),
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load continuity state: %s", e)
            return ContinuityState()

    def _save_state(self) -> None:
        """Persist state to disk."""
        try:
            CONTINUITY_DIR.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(
                json.dumps(asdict(self._state), ensure_ascii=False, indent=2)
            )
        except OSError as e:
            logger.error("Failed to save continuity state: %s", e)

    def _generate_briefing(self) -> None:
        """Generate condensed briefing from timeline for the last N hours."""
        if not TIMELINE_FILE.exists():
            return

        cutoff = time.time() - (self.briefing_hours * 3600)
        events: list[dict] = []

        try:
            with open(TIMELINE_FILE) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        if event.get("epoch", 0) >= cutoff:
                            events.append(event)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return

        if not events:
            return

        # Build briefing
        briefing = self._compose_briefing(events)

        try:
            BRIEFING_FILE.write_text(briefing)
        except OSError as e:
            logger.error("Failed to write briefing: %s", e)

    def _compose_briefing(self, events: list[dict]) -> str:
        """Compose markdown briefing from events."""
        now = datetime.now(timezone.utc)
        hours = self.briefing_hours

        # Group events by type
        by_type: dict[str, list[dict]] = {}
        for ev in events:
            t = ev.get("event_type", "unknown")
            by_type.setdefault(t, []).append(ev)

        # Group git events by project
        git_by_project: dict[str, list[dict]] = {}
        for ev in by_type.get("git_commit", []):
            proj = ev.get("project", "unknown")
            git_by_project.setdefault(proj, []).append(ev)

        # Build markdown
        lines: list[str] = [
            f"# 🧠 CORTEX Continuity Briefing",
            f"",
            f"> **Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}",
            f"> **Window:** Last {hours:.0f} hours ({len(events)} events)",
            f"> **Purpose:** Restore cognitive continuity for AI agent invocation",
            f"",
            f"---",
            f"",
        ]

        # === Git Activity ===
        git_commits = by_type.get("git_commit", [])
        if git_commits:
            lines.append("## 📦 Git Activity")
            lines.append("")
            for proj, proj_events in sorted(git_by_project.items()):
                lines.append(f"### `{proj}`")
                for ev in proj_events:
                    ts = ev.get("timestamp", "")[:16]
                    lines.append(f"- **{ts}** — {ev.get('summary', '')}")
                    if ev.get("detail"):
                        lines.append(f"  - `{ev['detail']}`")
                lines.append("")

        # === CORTEX Facts ===
        fact_events = by_type.get("fact_created", [])
        if fact_events:
            lines.append("## 🧠 CORTEX Memory Mutations")
            lines.append("")
            for ev in fact_events:
                ts = ev.get("timestamp", "")[:16]
                lines.append(f"- **{ts}** — {ev.get('summary', '')} (projects: {ev.get('project', 'n/a')})")
            lines.append("")

        # === Process Activity ===
        started = by_type.get("process_started", [])
        stopped = by_type.get("process_stopped", [])
        if started or stopped:
            lines.append("## ⚙️ Process Activity")
            lines.append("")
            for ev in started:
                ts = ev.get("timestamp", "")[:16]
                lines.append(f"- 🟢 **{ts}** — {ev.get('summary', '')}")
            for ev in stopped:
                ts = ev.get("timestamp", "")[:16]
                lines.append(f"- 🔴 **{ts}** — {ev.get('summary', '')}")
            lines.append("")

        # === File Activity ===
        file_events = by_type.get("file_activity", [])
        if file_events:
            lines.append("## 📝 File System Activity")
            lines.append("")
            total_modifications = sum(
                int(ev.get("summary", "0").split(" ")[0]) for ev in file_events
                if ev.get("summary", "").split(" ")[0].isdigit()
            )
            lines.append(f"- **{len(file_events)}** activity pulses, ~{total_modifications} file modifications total")
            # Show the most recent
            for ev in file_events[-5:]:
                ts = ev.get("timestamp", "")[:16]
                lines.append(f"- **{ts}** — {ev.get('summary', '')}")
            lines.append("")

        # === Continuity Gaps ===
        baselines = by_type.get("git_baseline", [])
        if baselines:
            lines.append("## 🆕 New Repositories Detected")
            lines.append("")
            for ev in baselines:
                lines.append(f"- `{ev.get('project', '')}` — {ev.get('summary', '')}")
            lines.append("")

        # === Summary Stats ===
        lines.append("## 📊 Summary")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|:-------|------:|")
        lines.append(f"| Total events | {len(events)} |")
        lines.append(f"| Git commits | {len(git_commits)} |")
        lines.append(f"| Fact mutations | {len(fact_events)} |")
        lines.append(f"| Process changes | {len(started) + len(stopped)} |")
        lines.append(f"| File activity pulses | {len(file_events)} |")
        lines.append(f"| Briefing window | {hours:.0f}h |")
        lines.append("")

        # === Actionable Briefing for AI ===
        lines.append("## 🎯 Agent Resumption Context")
        lines.append("")
        lines.append("When starting a new AI invocation, this briefing provides:")
        lines.append("")
        lines.append("1. **What changed** since the last session")
        lines.append("2. **Active work** (running processes indicate in-progress tasks)")
        lines.append("3. **Memory growth** (new facts = new decisions/errors/ghosts)")
        lines.append("4. **Gaps** (offline periods where events may have been missed)")
        lines.append("")

        return "\n".join(lines)

    # ─── Public query API ──────────────────────────────────────────

    @staticmethod
    def get_briefing() -> str:
        """Read the current briefing file."""
        if BRIEFING_FILE.exists():
            return BRIEFING_FILE.read_text()
        return "No continuity briefing available. Run `cortex continuity check` first."

    @staticmethod
    def get_timeline(hours: float = 8.0) -> list[dict]:
        """Read timeline events for the last N hours."""
        if not TIMELINE_FILE.exists():
            return []

        cutoff = time.time() - (hours * 3600)
        events: list[dict] = []
        try:
            with open(TIMELINE_FILE) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        if event.get("epoch", 0) >= cutoff:
                            events.append(event)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        return events
