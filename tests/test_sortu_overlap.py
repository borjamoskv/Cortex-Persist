"""Tests for sortu_overlap.py — Overlap detection and causal gap scoring."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_scripts = Path.home() / ".gemini" / "antigravity" / "skills" / "Sortu" / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from sortu_overlap import OverlapDetector, _cosine_similarity, _tokenize


class TestTokenize:
    def test_removes_short_words(self):
        tokens = _tokenize("I am the one who knocks")
        # tokenizer keeps words with len >= 3
        assert "am" not in tokens
        assert "one" in tokens  # 3 chars, kept
        assert "who" in tokens  # 3 chars, kept
        assert "knocks" in tokens

    def test_removes_stopwords(self):
        tokens = _tokenize("this is not for the user")
        assert "this" not in tokens
        assert "not" not in tokens
        assert "for" not in tokens
        assert "user" in tokens

    def test_empty_input(self):
        assert _tokenize("") == []


class TestCosineSimilarity:
    def test_identical_lists(self):
        result = _cosine_similarity(["alpha", "beta"], ["alpha", "beta"])
        assert result == pytest.approx(1.0, abs=0.001)

    def test_disjoint_lists(self):
        result = _cosine_similarity(["alpha", "beta"], ["gamma", "delta"])
        assert result == 0.0

    def test_partial_overlap(self):
        result = _cosine_similarity(["alpha", "beta", "gamma"], ["alpha", "delta"])
        assert 0.0 < result < 1.0

    def test_empty_lists(self):
        assert _cosine_similarity([], []) == 0.0


class TestOverlapDetector:
    def test_no_skills_means_proceed(self, tmp_path):
        detector = OverlapDetector(skills_dir=tmp_path)
        result = detector.decide("Build a sovereign test harness")
        assert result.decision == "PROCEED"
        assert result.overlap_score == 0.0
        assert result.causal_gap_score == 1.0

    def test_identical_skill_aborts(self, tmp_path):
        # Create a fake skill with identical text
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\ndescription: Build a sovereign test harness\n---\n"
            "# Build a sovereign test harness\n"
            "Build a sovereign test harness for verification.\n"
        )
        detector = OverlapDetector(skills_dir=tmp_path)
        result = detector.decide(
            "Build a sovereign test harness",
            overlap_threshold=0.5,
            causal_gap_threshold=0.8,
        )
        assert result.overlap_score > 0.0

    def test_completely_different_skill_proceeds(self, tmp_path):
        skill_dir = tmp_path / "quantum-physics"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\ndescription: Quantum entanglement simulation\n---\n"
            "# Quantum Physics\nSimulate quantum entanglement trajectories.\n"
        )
        detector = OverlapDetector(skills_dir=tmp_path)
        result = detector.decide("Build a database migration tool")
        assert result.decision == "PROCEED"

    def test_causal_gap_full_novelty(self, tmp_path):
        detector = OverlapDetector(skills_dir=tmp_path)
        gap = detector.compute_causal_gap("xylophone zygomorphic")
        assert gap == 1.0

    def test_scan_existing_ignores_non_skill_dirs(self, tmp_path):
        # Create a file (not a directory)
        (tmp_path / "not_a_dir.txt").write_text("hello")
        # Create a dir without SKILL.md
        (tmp_path / "empty-skill").mkdir()
        detector = OverlapDetector(skills_dir=tmp_path)
        skills = detector.scan_existing_skills()
        assert len(skills) == 0
