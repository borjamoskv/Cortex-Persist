"""Tests for cortex-core/ki_promoter.py - KI Context Promoter.

C5-REAL coverage for context detection, scoring, and promotion mechanisms.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

import ki_promoter


class TestContextDetection:
    @patch("subprocess.run")
    def test_detect_context_cortex(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "/path/to/cortex-persist\n"
        mock_run.return_value = mock_result

        with patch.dict("os.environ", {}, clear=True):
            ctx = ki_promoter.detect_context()
            assert ctx["project"] == "cortex-persist"
            assert ctx["domain"] == "cortex"
            assert "persistence" in ctx["tags"]
            assert "c5-real" in ctx["tags"]  # ALWAYS_RELEVANT

    @patch("subprocess.run")
    def test_detect_context_bounty_active_file(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        with patch.dict("os.environ", {"CORTEX_ACTIVE_FILE": "bounty_report.md"}):
            ctx = ki_promoter.detect_context()
            assert ctx["domain"] == "security"
            assert "immunefi" in ctx["tags"]


class TestKIScoring:
    def test_score_ki_perfect_match(self):
        meta = {"tags": ["bounty", "security"], "domain": "security", "access_count": 0}
        ctx = {"tags": {"bounty", "security"}, "domain": "security"}
        ki = ki_promoter.score_ki(meta, Path("/fake/path"), ctx)
        # Tag overlap: 2/2 = 1.0. Domain match = 1.0. Freshness = 0.1 (fallback)
        # Score = (1.0 * 0.5) + (1.0 * 0.3) + (0.1 * 0.2) = 0.5 + 0.3 + 0.02 = 0.82
        assert ki.tag_score == 1.0
        assert ki.domain_score == 1.0
        assert ki.score >= 0.8

    def test_score_ki_freshness(self):
        recent = datetime.now(timezone.utc).isoformat()
        old = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        ctx = {"tags": {"test"}, "domain": "test"}

        meta_recent = {"tags": ["test"], "domain": "test", "last_accessed": recent}
        meta_old = {"tags": ["test"], "domain": "test", "last_accessed": old}

        ki_recent = ki_promoter.score_ki(meta_recent, Path("/fake/path1"), ctx)
        ki_old = ki_promoter.score_ki(meta_old, Path("/fake/path2"), ctx)

        # Recent should have higher freshness score (~1.0 vs ~0.5)
        assert ki_recent.freshness_score > ki_old.freshness_score
        assert ki_recent.score > ki_old.score

    def test_score_ki_access_count_boost(self):
        meta = {"tags": ["test"], "domain": "test", "access_count": 25}
        ctx = {"tags": {"test"}, "domain": "test"}

        ki = ki_promoter.score_ki(meta, Path("/fake/path"), ctx)
        # With access_count > 20, it gets two 1.1x boosts
        assert ki.score > 0.82  # Greater than base perfect match


class TestKIPromotion:
    def test_promote_ki(self, tmp_path):
        meta_file = tmp_path / "metadata.json"
        meta_file.write_text('{"domain": "test", "access_count": 5}')

        ki = ki_promoter.ScoredKI(
            name="test_ki",
            path=meta_file,
            score=1.0,
            tag_score=1.0,
            domain_score=1.0,
            freshness_score=1.0,
        )

        ki_promoter.promote_ki(ki)

        # Verify metadata updated
        updated = json.loads(meta_file.read_text())
        assert "last_accessed" in updated
        assert updated["access_count"] == 6
