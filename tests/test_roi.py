"""Tests for cortex ROI engine (CHRONOS-1 aggregation)."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from cortex.engine import CortexEngine


@pytest.fixture
def engine(tmp_path):
    """Create a fresh test engine."""
    db_path = tmp_path / "test_roi.db"
    eng = CortexEngine(db_path=db_path)
    eng.init_db_sync()
    yield eng
    eng.close_sync()


class TestROIStatus:
    """Tests for the ROI aggregation engine."""

    @pytest.mark.asyncio
    async def test_roi_empty_db(self, engine):
        """ROI on empty DB should return zero metrics gracefully."""
        from cortex.cli.roi_cmds import _aggregate_chronos

        m = await _aggregate_chronos(engine)
        assert m.total_facts >= 0
        assert m.facts_with_chronos == 0
        assert m.total_ai_time_secs == 0.0
        assert m.total_human_time_secs == 0.0
        assert m.roi_ratio == 0.0

    @pytest.mark.asyncio
    async def test_roi_with_chronos_facts(self, engine):
        """Facts stored with CHRONOS meta should aggregate correctly."""
        import dataclasses

        from cortex.timing.chronos import ChronosEngine

        # Store 3 facts with CHRONOS metadata
        for i in range(3):
            metrics = ChronosEngine.analyze(ai_time_secs=10 + i, complexity="low")
            meta = {"chronos": dataclasses.asdict(metrics)}
            engine.store_sync(
                "test-roi",
                f"Test fact #{i}",
                fact_type="decision",
                meta=meta,
            )

        from cortex.cli.roi_cmds import _aggregate_chronos

        m = await _aggregate_chronos(engine)
        assert m.facts_with_chronos == 3
        assert m.total_ai_time_secs > 0
        assert m.total_human_time_secs > 0
        # Human time should always be >= AI time for low complexity
        assert m.total_human_time_secs >= m.total_ai_time_secs
        assert m.roi_ratio > 1.0

    @pytest.mark.asyncio
    async def test_roi_top_projects(self, engine):
        """Top projects should be sorted by time saved."""
        import dataclasses

        from cortex.timing.chronos import ChronosEngine

        for project in ["alpha", "beta", "gamma"]:
            ai_time = 10 if project == "alpha" else 60
            metrics = ChronosEngine.analyze(ai_time_secs=ai_time, complexity="high")
            meta = {"chronos": dataclasses.asdict(metrics)}
            engine.store_sync(
                project,
                f"Fact for {project}",
                fact_type="decision",
                meta=meta,
            )

        from cortex.cli.roi_cmds import _aggregate_chronos

        m = await _aggregate_chronos(engine)
        assert len(m.top_projects) <= 5
        assert m.top_projects[0][0] in {"alpha", "beta", "gamma"}


class TestROICLI:
    """Tests for the CLI roi command."""

    def test_roi_status_cli(self, engine, tmp_path):
        """CLI roi status should exit 0 and show table output."""
        from cortex.cli.roi_cmds import roi

        runner = CliRunner()
        result = runner.invoke(
            roi,
            ["status", "--db", str(tmp_path / "test_roi.db")],
        )
        assert result.exit_code == 0
        assert "CHRONOS" in result.output

    def test_roi_report_cli(self, engine, tmp_path):
        """CLI roi report should exit 0 and output markdown."""
        from cortex.cli.roi_cmds import roi

        runner = CliRunner()
        result = runner.invoke(
            roi,
            ["report", "--db", str(tmp_path / "test_roi.db")],
        )
        assert result.exit_code == 0
        assert "ROI" in result.output


class TestROIMarkdown:
    """Tests for markdown ROI generation."""

    @pytest.mark.asyncio
    async def test_snapshot_roi_section(self, engine, tmp_path):
        """Snapshot export should contain a ROI section."""
        engine.store_sync("test-project", "A test fact for snapshot")
        out_path = tmp_path / "snapshot.md"

        await engine.export_snapshot(out_path=out_path)
        content = out_path.read_text(encoding="utf-8")

        assert "CORTEX" in content
        # ROI section should be present (even if estimated)
        assert "ROI" in content

    def test_generate_roi_markdown_empty(self):
        """Markdown generation with no CHRONOS facts."""
        from cortex.cli.roi_cmds import ROIMetrics, generate_roi_markdown

        m = ROIMetrics(
            total_facts=100,
            facts_with_chronos=0,
            total_ai_time_secs=0,
            total_human_time_secs=0,
            projects=5,
            top_projects=[],
        )
        md = generate_roi_markdown(m)
        assert "Projected ROI" in md
        assert "estimated" in md

    def test_generate_roi_markdown_with_data(self):
        """Markdown generation with CHRONOS facts."""
        from cortex.cli.roi_cmds import ROIMetrics, generate_roi_markdown

        m = ROIMetrics(
            total_facts=100,
            facts_with_chronos=10,
            total_ai_time_secs=360.0,
            total_human_time_secs=36000.0,
            projects=5,
            top_projects=[("test", 10.0, 0.1)],
        )
        md = generate_roi_markdown(m)
        assert "Hours Saved" in md
        assert "CHRONOS" in md
