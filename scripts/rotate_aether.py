#!/usr/bin/env python3
"""Aether Dynamic Profile Rotation — CORTEX

Reads the CORTEX memory snapshot to determine context weight (active facts).
Dynamically rotates the Aether agent profile to prevent token exhaustion.
"""

import logging
import os
import re
import sys
from pathlib import Path

# Paths
CORTEX_HOME = Path.home() / ".cortex"
SNAPSHOT_FILE = CORTEX_HOME / "context-snapshot.md"
CORTEX_SRC = Path(".")
PROFILES_DIR = CORTEX_SRC / "cortex" / "agents" / "definitions" / "profiles"
TARGET_PROFILE = CORTEX_SRC / "cortex" / "agents" / "definitions" / "aether.yaml"

LIGHT_PROFILE = PROFILES_DIR / "aether_light.yaml"
HEAVY_PROFILE = PROFILES_DIR / "aether_heavy.yaml"

# Threshold
HEAVY_THRESHOLD_FACTS = 2000

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("aether-rotation")


def get_active_facts() -> int:
    """Extract the active facts count from the context snapshot."""
    if not SNAPSHOT_FILE.exists():
        logger.warning("Snapshot not found at %s. Defaulting to 0 facts.", SNAPSHOT_FILE)
        return 0

    try:
        content = SNAPSHOT_FILE.read_text(encoding="utf-8")
        # Look for "> Total: XXX facts activos" or "- **Facts activos:** XXX"
        match = re.search(r"Facts activos:\s*(\d+)", content, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Fallback check
        match = re.search(r">\s*Total:\s*(\d+)\s*facts activos", content, re.IGNORECASE)
        if match:
            return int(match.group(1))

    except Exception as e:
        logger.error("Failed to read snapshot: %s", e)

    logger.warning("Could not parse active facts count. Defaulting to 0.")
    return 0


def record_decision(msg: str) -> None:
    """Record a decision in the CORTEX database."""
    try:
        import subprocess

        subprocess.run(
            [
                sys.executable,
                "-m",
                "cortex.cli",
                "store",
                "--type",
                "decision",
                "--source",
                "agent:system",
                "AETHER-ROTATION",
                msg,
            ],
            cwd=str(CORTEX_SRC),
            capture_output=True,
            timeout=10,
        )
    except Exception as e:
        logger.debug("Failed to record decision via CLI: %s", e)


def main():
    logger.info("Starting Aether Dynamic Profile Rotation...")

    if not LIGHT_PROFILE.exists() or not HEAVY_PROFILE.exists():
        logger.error("Missing profile definitions in cortex/agents/definitions/profiles/")
        sys.exit(1)

    active_facts = get_active_facts()
    logger.info("Detected Active Facts: %s", active_facts)

    if active_facts > HEAVY_THRESHOLD_FACTS:
        logger.info("Context weight is HIGH (> %s). Selecting LIGHT profile.", HEAVY_THRESHOLD_FACTS)
        source_profile = LIGHT_PROFILE
        profile_type = "LIGHT"
    else:
        logger.info(
            "Context weight is NORMAL (<= %s). Selecting HEAVY profile.", HEAVY_THRESHOLD_FACTS
        )
        source_profile = HEAVY_PROFILE
        profile_type = "HEAVY"

    # Check current profile to avoid unnecessary filesystem writes
    current_symlink_target = None
    if TARGET_PROFILE.exists() or TARGET_PROFILE.is_symlink():
        if TARGET_PROFILE.is_symlink():
            current_symlink_target = TARGET_PROFILE.readlink()
            if current_symlink_target == source_profile:
                logger.info(
                    "Aether is already using the %s profile. No action needed.", profile_type
                )
                return
        else:
            # We don't want to destroy a valid file if it's not a symlink, so copy the content.
            # Compare contents to skip overwrite
            try:
                if TARGET_PROFILE.read_bytes() == source_profile.read_bytes():
                    logger.info(
                        "Aether is already using the %s profile content. No action needed.",
                        profile_type,
                    )
                    return
            except Exception:
                pass

    try:
        if TARGET_PROFILE.exists() or TARGET_PROFILE.is_symlink():
            if TARGET_PROFILE.is_symlink():
                TARGET_PROFILE.unlink()
            else:
                TARGET_PROFILE.unlink()  # Delete existing text file

        # Symlink is the cleanest approach, dynamic reloading via OS.
        os.symlink(source_profile, TARGET_PROFILE)
        msg = (
            f"Aether dynamically rotated to {profile_type} profile (Active facts: {active_facts})."
        )
        logger.info(msg)
        record_decision(msg)
        print(f"✅ {msg}")

    except Exception as e:
        logger.error("Failed to rotate profile: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
