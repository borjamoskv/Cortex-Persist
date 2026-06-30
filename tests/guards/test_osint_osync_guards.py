# [C5-REAL] Exergy-Maximized
"""
Unit tests for OSINTGuard and OSYNCGuard.
"""

from __future__ import annotations

import io
import os
import pytest
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

from babylon60.guards.osint_guard import OSINTGuard, OSINTViolationError
from babylon60.guards.osync_guard import OSYNCGuard, OSYNCViolationError


def test_osint_guard_verify_clean_text() -> None:
    # 1. Clean content passes
    OSINTGuard.verify_clean_text("This is an exergy-maximized fact with zero leaks.")

    # 2. Literal PII fails
    target_pii = "".join(["borja", "fernandez", "angulo"])
    with pytest.raises(OSINTViolationError, match="PII Containment Breach"):
        OSINTGuard.verify_clean_text(f"Dato clasificado del operador: {target_pii}")

    # 3. Raw user directory paths fail
    with pytest.raises(OSINTViolationError, match="PII Leak"):
        OSINTGuard.verify_clean_text("Exposed directory /Users/borja/10_PROJECTS/")


def test_osint_guard_mask_system_paths() -> None:
    target_pii = "".join(["borja", "fernandez", "angulo"])
    raw_path = f"/Users/{target_pii}/30_CORTEX/docs/epistemology/100_osync_osint.md"
    clean_path = OSINTGuard.mask_system_paths(raw_path)

    assert clean_path == "$HOME/30_CORTEX/docs/epistemology/100_osync_osint.md"


@pytest.mark.skipif(Image is None, reason="PIL/Pillow not installed")
def test_osint_guard_verify_and_strip_image() -> None:
    # Generate 1x1 pixel image with dummy metadata
    assert Image is not None
    img = Image.new("RGB", (1, 1), color="red")
    exif_data = img.getexif()
    exif_data[271] = "MakerTag"  # Document name tag/make

    img_bytes_io = io.BytesIO()
    img.save(img_bytes_io, format="JPEG", exif=exif_data)
    raw_bytes = img_bytes_io.getvalue()

    # Verify metadata is stripped
    clean_bytes = OSINTGuard.verify_and_strip_image(raw_bytes)

    clean_img = Image.open(io.BytesIO(clean_bytes))
    assert not clean_img.getexif()


def test_osync_guard_verify_nexus_symlink(tmp_path: Path) -> None:
    src_file = tmp_path / "source.txt"
    src_file.write_text("Sovereign data.")

    link_file = tmp_path / "link.txt"

    # 1. Non-existent symlink raises error
    with pytest.raises(OSYNCViolationError, match="must be a symlink"):
        OSYNCGuard.verify_nexus_symlink(link_file, src_file)

    # 2. Existing file (not a symlink) raises error
    link_file.write_text("Duplicate data.")
    with pytest.raises(OSYNCViolationError, match="must be a symlink"):
        OSYNCGuard.verify_nexus_symlink(link_file, src_file)

    # 3. Correct symlink passes
    link_file.unlink()
    os.symlink(src_file, link_file)
    OSYNCGuard.verify_nexus_symlink(link_file, src_file)


def test_osync_guard_verify_git_clean(tmp_path: Path) -> None:
    # Non-git directory check
    with pytest.raises(OSYNCViolationError, match="Git execution failure"):
        OSYNCGuard.verify_git_clean(tmp_path)


def test_osync_guard_verify_lamport_ordering() -> None:
    # 1. Correct sync increments
    new_clock = OSYNCGuard.verify_lamport_ordering(local_clock=5, remote_clock=7)
    assert new_clock == 8

    new_clock2 = OSYNCGuard.verify_lamport_ordering(local_clock=10, remote_clock=4)
    assert new_clock2 == 11

    # 2. Negative values fail
    with pytest.raises(OSYNCViolationError, match="non-negative"):
        OSYNCGuard.verify_lamport_ordering(-1, 5)
