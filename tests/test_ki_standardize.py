"""Tests for cortex-core/ki_standardize.py - KI Schema Standardizer.

C5-REAL coverage for domain inference, timestamp normalization, and schema standardization.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

import ki_standardize


class TestKIStandardize:
    def test_infer_domain(self):
        assert ki_standardize.infer_domain(["bounty", "immunefi"]) == "security"
        assert ki_standardize.infer_domain(["cortex", "ai-agent"]) == "cortex"
        assert ki_standardize.infer_domain(["music"]) == "multimedia"
        assert ki_standardize.infer_domain(["random", "tags"]) == "general"

    def test_normalize_timestamp(self):
        # Epoch time
        ts = ki_standardize.normalize_timestamp(1700000000.0)
        assert "2023-11-14" in ts
        assert "+00:00" in ts

        # String ISO
        iso_str = "2026-05-26T12:00:00+00:00"
        assert ki_standardize.normalize_timestamp(iso_str) == iso_str

        # None/Empty
        assert ki_standardize.normalize_timestamp(None) is None
        assert ki_standardize.normalize_timestamp("") is None

    def test_standardize_ki(self):
        meta = {
            "name": "Legacy KI",
            "date_created": 1700000000.0,
            "tags": ["web3", "defi"],
            "vulnerabilities": ["Reentrancy"],
            "random_field": "drop me",
        }

        mock_path = MagicMock(spec=Path)
        mock_stat = MagicMock()
        mock_stat.st_birthtime = 1700000000.0
        mock_stat.st_mtime = 1700000000.0
        mock_stat.st_atime = 1700000000.0
        mock_path.stat.return_value = mock_stat

        normalized, changes = ki_standardize.standardize_ki(meta, mock_path)

        assert normalized["title"] == "Legacy KI"
        assert normalized["domain"] == "web3"
        assert "created_at" in normalized
        assert normalized["vulnerabilities"] == ["Reentrancy"]  # Preserved field
        assert "random_field" not in normalized  # Dropped field
        assert "date_created" not in normalized  # Replaced
        assert normalized["access_count"] == 0

        changes_str = " ".join(changes)
        assert "date_created → created_at" in changes_str
        assert "domain inferred: web3" in changes_str
        assert "name" in changes_str and "random_field" in changes_str and "dropped" in changes_str

    def test_standardize_ki_oversized_summary(self):
        meta = {"title": "Big Summary", "summary": "A" * 600}
        mock_path = MagicMock(spec=Path)
        mock_stat = MagicMock()
        mock_stat.st_mtime = 1700000000.0
        mock_stat.st_atime = 1700000000.0
        mock_stat.st_birthtime = 1700000000.0
        mock_path.stat.return_value = mock_stat

        normalized, changes = ki_standardize.standardize_ki(meta, mock_path)

        assert len(normalized["summary"]) == 600
        assert any(">500" in c for c in changes)
