"""Shared native path resolution for Cortex-Persist scripts.

Resolution order is stable across all binaries:
1. Explicit environment variable override.
2. Executable present on ``PATH``.
3. Repo-local cache in ``build/native/bin``.
4. Cargo release output in ``engine/cortex-core/target/release``.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUILD_NATIVE_BIN = PROJECT_ROOT / "build" / "native" / "bin"
CORE_RELEASE_BIN = PROJECT_ROOT / "engine" / "cortex-core" / "target" / "release"


def resolve_native_binary(binary_name: str, *env_vars: str) -> Path | None:
    """Resolve a native executable from env, PATH, or repo-local locations."""
    for env_var in env_vars:
        override = os.environ.get(env_var)
        if not override:
            continue
        candidate = Path(override).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

    discovered = shutil.which(binary_name)
    if discovered:
        return Path(discovered)

    for candidate in (
        BUILD_NATIVE_BIN / binary_name,
        CORE_RELEASE_BIN / binary_name,
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

    return None


def resolve_project_script(script_name: str, *env_vars: str) -> Path | None:
    """Resolve a script under ``scripts/`` with optional env override."""
    for env_var in env_vars:
        override = os.environ.get(env_var)
        if not override:
            continue
        candidate = Path(override).expanduser()
        if candidate.is_file():
            return candidate

    candidate = PROJECT_ROOT / "scripts" / script_name
    if candidate.is_file():
        return candidate
    return None
