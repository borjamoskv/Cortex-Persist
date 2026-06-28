# [C5-REAL] Exergy-Maximized

import os
from pathlib import Path

import pytest

from cortex.extensions.nexus.symlink_engine import SymlinkEngine


def test_symlink_engine_file_propagation(tmp_path: Path):
    """Test that SymlinkEngine replaces a physical file with a symlink."""
    canonical = tmp_path / "CORTEX"
    satellite = tmp_path / "SATELLITE"

    canonical.mkdir()
    satellite.mkdir()

    # Create canonical artifact
    artifact_path = canonical / "AGENTS.md"
    artifact_path.write_text("CORTEX_CANONICAL_CONTENT")

    # Create a conflicting physical file in satellite
    satellite_artifact = satellite / "AGENTS.md"
    satellite_artifact.write_text("SATELLITE_ROT_CONTENT")

    # Enforce link
    engine = SymlinkEngine(str(canonical))
    results = engine.propagate([str(satellite)], ["AGENTS.md"])

    assert results[str(satellite)] is True

    # Verify satellite now has a symlink pointing to canonical
    assert satellite_artifact.is_symlink()
    assert os.readlink(str(satellite_artifact)) == str(artifact_path)

    # Verify backup was created
    backup = satellite / "AGENTS.md.nexus_bak"
    assert backup.exists()
    assert backup.read_text() == "SATELLITE_ROT_CONTENT"

    # Verify invariants pass
    assert engine.validate_invariants([str(satellite)], ["AGENTS.md"]) is True


def test_symlink_engine_directory_propagation(tmp_path: Path):
    """Test that SymlinkEngine backs up and symlinks entire directories."""
    canonical = tmp_path / "CORTEX"
    satellite = tmp_path / "SATELLITE"

    canonical.mkdir()
    satellite.mkdir()

    canonical_dir = canonical / "skills"
    canonical_dir.mkdir()
    (canonical_dir / "test.txt").write_text("skill")

    satellite_dir = satellite / "skills"
    satellite_dir.mkdir()
    (satellite_dir / "rot.txt").write_text("rot")

    engine = SymlinkEngine(str(canonical))
    results = engine.propagate([str(satellite)], ["skills"])

    assert results[str(satellite)] is True

    # Verify satellite_dir is now a symlink
    assert satellite_dir.is_symlink()
    assert os.readlink(str(satellite_dir)) == str(canonical_dir)

    # Verify backup tree exists
    backup = satellite / "skills.nexus_bak"
    assert backup.is_dir()
    assert (backup / "rot.txt").exists()


def test_symlink_engine_missing_canonical(tmp_path: Path):
    """Test behavior when the canonical file does not exist."""
    canonical = tmp_path / "CORTEX"
    satellite = tmp_path / "SATELLITE"

    canonical.mkdir()
    satellite.mkdir()

    engine = SymlinkEngine(str(canonical))
    results = engine.propagate([str(satellite)], ["MISSING.md"])

    assert results[str(satellite)] is False


def test_symlink_engine_validate_invariants_fails(tmp_path: Path):
    """Test that validate_invariants fails when physical redundancy exists."""
    canonical = tmp_path / "CORTEX"
    satellite = tmp_path / "SATELLITE"

    canonical.mkdir()
    satellite.mkdir()

    # Create canonical artifact
    artifact_path = canonical / "AGENTS.md"
    artifact_path.write_text("CORTEX_CANONICAL_CONTENT")

    # Create a conflicting physical file in satellite
    satellite_artifact = satellite / "AGENTS.md"
    satellite_artifact.write_text("SATELLITE_ROT_CONTENT")

    engine = SymlinkEngine(str(canonical))
    # Do NOT propagate

    # Should fail validation
    assert engine.validate_invariants([str(satellite)], ["AGENTS.md"]) is False
