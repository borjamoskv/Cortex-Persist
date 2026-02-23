"""
CORTEX v4.0 — Perception System Tests.

Tests for file classification, behavioral inference, event statistics,
perception recording, and the full pipeline.
"""

import os
import tempfile
import time

import pytest

from cortex.engine import CortexEngine
from cortex.perception import (
    BehavioralSnapshot,
    FileEvent,
    PerceptionPipeline,
    PerceptionRecorder,
    classify_file,
    compute_event_stats,
    infer_behavior,
    infer_project_from_path,
    should_ignore,
)

# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
async def engine():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    eng = CortexEngine(db_path=db_path, auto_embed=False)
    await eng.init_db()
    yield eng
    await eng.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


def _make_event(
    path: str = "/workspace/proj/src/main.py",
    event_type: str = "modified",
    role: str | None = None,
    project: str | None = "proj",
    ts_offset: float = 0,
) -> FileEvent:
    """Create a test FileEvent."""
    return FileEvent(
        path=path,
        event_type=event_type,
        role=role or classify_file(path),
        project=project,
        timestamp=time.monotonic() + ts_offset,
    )


# ─── File Classification Tests ───────────────────────────────────────


class TestFileClassification:
    def test_python_source(self):
        assert classify_file("/workspace/app/main.py") == "source"

    def test_typescript_source(self):
        assert classify_file("/workspace/app/index.tsx") == "source"

    def test_test_file(self):
        assert classify_file("/workspace/tests/test_main.py") == "test"

    def test_spec_file(self):
        assert classify_file("/workspace/tests/main.spec.ts") == "test"

    def test_config_toml(self):
        assert classify_file("/workspace/pyproject.toml") == "config"

    def test_config_env(self):
        assert classify_file("/workspace/.env.local") == "config"

    def test_config_json(self):
        assert classify_file("/workspace/package.json") == "config"

    def test_docs_markdown(self):
        assert classify_file("/workspace/README.md") == "docs"

    def test_docs_txt(self):
        assert classify_file("/workspace/CHANGELOG.txt") == "docs"

    def test_asset_image(self):
        assert classify_file("/workspace/public/logo.png") == "asset"

    def test_unknown_file(self):
        assert classify_file("/workspace/.gitignore") == "unknown"


class TestProjectInference:
    def test_infer_from_workspace(self):
        result = infer_project_from_path("/workspace/cortex/src/main.py", "/workspace")
        assert result == "cortex"

    def test_infer_single_level(self):
        result = infer_project_from_path("/workspace/file.py", "/workspace")
        assert result == "workspace"

    def test_fallback_parent(self):
        result = infer_project_from_path("/some/deep/path/file.py")
        assert result == "path"


class TestIgnorePatterns:
    def test_ignore_git(self):
        assert should_ignore("/workspace/.git/HEAD")

    def test_ignore_pycache(self):
        assert should_ignore("/workspace/__pycache__/mod.pyc")

    def test_ignore_node_modules(self):
        assert should_ignore("/workspace/node_modules/pkg/index.js")

    def test_allow_normal(self):
        assert not should_ignore("/workspace/cortex/main.py")

    def test_ignore_venv(self):
        assert should_ignore("/workspace/.venv/lib/pkg.py")


# ─── Event Statistics Tests ──────────────────────────────────────────


class TestComputeStats:
    def test_empty_events(self):
        stats = compute_event_stats([])
        assert stats["total"] == 0

    def test_single_event(self):
        events = [_make_event()]
        stats = compute_event_stats(events)
        assert stats["total"] == 1
        assert stats["source_ratio"] == 1.0

    def test_mixed_roles(self):
        events = [
            _make_event("/w/p/test_foo.py"),  # test
            _make_event("/w/p/test_bar.py"),  # test
            _make_event("/w/p/main.py"),  # source
            _make_event("/w/p/pyproject.toml"),  # config
        ]
        stats = compute_event_stats(events)
        assert stats["total"] == 4
        assert stats["test_ratio"] == 0.5
        assert stats["source_ratio"] == 0.25
        assert stats["config_ratio"] == 0.25

    def test_unique_files_and_dirs(self):
        events = [
            _make_event("/w/a/f1.py"),
            _make_event("/w/a/f2.py"),
            _make_event("/w/b/f3.py"),
        ]
        stats = compute_event_stats(events)
        assert stats["unique_files"] == 3
        assert stats["unique_dirs"] == 2


# ─── Behavioral Inference Tests ──────────────────────────────────────


class TestBehavioralInference:
    def test_insufficient_data(self):
        events = [_make_event(), _make_event()]
        snapshot = infer_behavior(events)
        assert snapshot.intent == "unknown"
        assert snapshot.confidence == "C1"

    def test_debugging_detection(self):
        """Many test files → debugging intent."""
        events = [_make_event("/w/p/test_a.py", ts_offset=i) for i in range(5)] + [
            _make_event("/w/p/main.py", ts_offset=6)
        ]

        snapshot = infer_behavior(events)
        assert snapshot.intent == "debugging"
        assert snapshot.emotion == "cautious"
        assert snapshot.confidence == "C4"

    def test_config_setup_detection(self):
        """Config files dominate → setup intent."""
        events = [_make_event("/w/p/pyproject.toml", ts_offset=i) for i in range(4)] + [
            _make_event("/w/p/main.py", ts_offset=5)
        ]

        snapshot = infer_behavior(events)
        assert snapshot.intent == "setup"
        assert snapshot.emotion == "neutral"

    def test_frustrated_iteration(self):
        """Same file saved repeatedly → frustrated."""
        events = [_make_event("/w/p/main.py", ts_offset=i) for i in range(6)]
        snapshot = infer_behavior(events)
        assert snapshot.intent == "frustrated_iteration"
        assert snapshot.emotion == "frustrated"

    def test_documentation_detection(self):
        """Docs files dominate → documenting."""
        events = [
            _make_event("/w/p/README.md", ts_offset=0),
            _make_event("/w/p/docs/guide.md", ts_offset=1),
            _make_event("/w/p/CHANGELOG.md", ts_offset=2),
            _make_event("/w/p/main.py", ts_offset=3),
        ]
        snapshot = infer_behavior(events)
        assert snapshot.intent == "documenting"
        assert snapshot.emotion == "confident"

    def test_generic_activity(self):
        """No strong pattern → generic active."""
        events = [
            _make_event("/w/p/a.py", ts_offset=0),
            _make_event("/w/p/b.css", ts_offset=1),
            _make_event("/w/p/c.html", ts_offset=2),
        ]
        snapshot = infer_behavior(events)
        assert snapshot.intent == "active"
        assert snapshot.confidence == "C2"

    def test_snapshot_to_dict(self):
        events = [_make_event(ts_offset=i) for i in range(5)]
        snapshot = infer_behavior(events)
        d = snapshot.to_dict()
        assert "intent" in d
        assert "emotion" in d
        assert "confidence" in d
        assert "event_count" in d


# ─── Perception Recorder Tests ───────────────────────────────────────


@pytest.mark.asyncio
class TestPerceptionRecorder:
    async def test_record_high_confidence(self, engine):
        from cortex.episodic import EpisodicMemory

        conn = await engine.get_conn()
        recorder = PerceptionRecorder(conn, "test-session", cooldown_s=0)

        snapshot = BehavioralSnapshot(
            intent="debugging",
            emotion="cautious",
            confidence="C4",
            project="cortex",
            event_count=5,
            window_seconds=60,
            top_files=["test_main.py"],
            summary="Debugging session on cortex",
            timestamp="2024-01-01T00:00:00",
        )

        ep_id = await recorder.maybe_record(snapshot)
        assert ep_id is not None
        assert ep_id > 0

        # Verify in DB
        memory = EpisodicMemory(conn)
        episodes = await memory.recall(project="cortex")
        assert len(episodes) == 1
        assert episodes[0].emotion == "cautious"
        assert "auto-perceived" in episodes[0].tags

    async def test_skip_low_confidence(self, engine):
        conn = await engine.get_conn()
        recorder = PerceptionRecorder(conn, "test-session", cooldown_s=0)

        snapshot = BehavioralSnapshot(
            intent="unknown",
            emotion="neutral",
            confidence="C1",
            project="cortex",
            event_count=2,
            window_seconds=10,
            top_files=[],
            summary="Insufficient data",
            timestamp="2024-01-01T00:00:00",
        )

        ep_id = await recorder.maybe_record(snapshot)
        assert ep_id is None

    async def test_cooldown_rate_limiting(self, engine):
        conn = await engine.get_conn()
        recorder = PerceptionRecorder(conn, "test-session", cooldown_s=300)

        snapshot = BehavioralSnapshot(
            intent="debugging",
            emotion="cautious",
            confidence="C4",
            project="cortex",
            event_count=5,
            window_seconds=60,
            top_files=[],
            summary="First record",
            timestamp="2024-01-01T00:00:00",
        )

        # First should record
        first = await recorder.maybe_record(snapshot)
        assert first is not None

        # Second should be rate-limited
        second = await recorder.maybe_record(snapshot)
        assert second is None

    async def test_different_projects_not_rate_limited(self, engine):
        conn = await engine.get_conn()
        recorder = PerceptionRecorder(conn, "test-session", cooldown_s=300)

        snap_a = BehavioralSnapshot(
            intent="debugging",
            emotion="cautious",
            confidence="C4",
            project="project-a",
            event_count=5,
            window_seconds=60,
            top_files=[],
            summary="A",
            timestamp="2024-01-01T00:00:00",
        )
        snap_b = BehavioralSnapshot(
            intent="debugging",
            emotion="cautious",
            confidence="C4",
            project="project-b",
            event_count=5,
            window_seconds=60,
            top_files=[],
            summary="B",
            timestamp="2024-01-01T00:00:00",
        )

        a = await recorder.maybe_record(snap_a)
        b = await recorder.maybe_record(snap_b)
        assert a is not None
        assert b is not None


# ─── Pipeline Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestPerceptionPipeline:
    async def test_pipeline_tick_no_events(self, engine):
        conn = await engine.get_conn()
        pipeline = PerceptionPipeline(conn, "test-session", "/tmp")
        result = await pipeline.tick()
        assert result is None

    async def test_pipeline_tick_with_events(self, engine):
        conn = await engine.get_conn()
        pipeline = PerceptionPipeline(
            conn,
            "test-session",
            "/tmp",
            cooldown_s=0,
        )

        # Simulate events directly
        for i in range(5):
            pipeline._events.append(_make_event(f"/tmp/test_file{i}.py", ts_offset=i))

        result = await pipeline.tick()
        assert result is not None
        assert isinstance(result, BehavioralSnapshot)

    async def test_pipeline_event_count(self, engine):
        conn = await engine.get_conn()
        pipeline = PerceptionPipeline(conn, "test-session", "/tmp")
        assert pipeline.event_count == 0

        pipeline._events.append(_make_event())
        assert pipeline.event_count == 1

    async def test_pipeline_window_pruning(self, engine):
        conn = await engine.get_conn()
        pipeline = PerceptionPipeline(
            conn,
            "test-session",
            "/tmp",
            window_s=60,
        )

        # Add old event (outside window)
        old_event = _make_event(ts_offset=-120)
        pipeline._events.append(old_event)

        # Add recent event
        pipeline._events.append(_make_event())

        events = pipeline.get_window_events()
        assert len(events) == 1  # old event pruned
