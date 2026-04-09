#!/usr/bin/env python3
"""Run local release preflight checks for the root ``cortex-persist`` package.

This script validates the package version, optional Git tag, worktree state, and
distribution artifacts before a PyPI release. It is designed to be reusable both
locally and from CI so the release workflow and manual release steps follow the
same deterministic checks.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DEFAULT_PYPROJECT: Final[Path] = REPO_ROOT / "pyproject.toml"
DEFAULT_DIST_DIR: Final[Path] = REPO_ROOT / "dist"
DEFAULT_NPM_PACKAGE_DIR: Final[Path] = REPO_ROOT / "sdks" / "js"


def normalize_artifact_stem(project_name: str) -> str:
    """Return the normalized artifact stem used by wheel and sdist filenames."""
    normalized_name = re.sub(r"[-_.]+", "_", project_name.strip())
    if not normalized_name:
        raise ValueError("Project name cannot be empty.")
    return normalized_name


def load_project_metadata(pyproject_path: Path) -> tuple[str, str]:
    """Load the root project name and version from ``pyproject.toml``."""
    if not pyproject_path.is_file():
        raise FileNotFoundError(f"pyproject file not found: {pyproject_path}")

    with pyproject_path.open("rb") as handle:
        payload = tomllib.load(handle)

    project = payload.get("project")
    if not isinstance(project, dict):
        raise ValueError(f"Missing [project] table in {pyproject_path}")

    name = project.get("name")
    version = project.get("version")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Missing project.name in {pyproject_path}")
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"Missing project.version in {pyproject_path}")

    return name.strip(), version.strip()


def expected_release_tag(version: str) -> str:
    """Return the release tag expected for a package version."""
    normalized_version = version.strip()
    if not normalized_version:
        raise ValueError("Project version cannot be empty.")
    return f"v{normalized_version}"


def validate_release_tag(version: str, tag: str) -> str:
    """Validate that a Git tag matches the package version."""
    normalized_tag = tag.strip()
    if not normalized_tag:
        raise ValueError("Release tag cannot be empty.")

    expected_tag = expected_release_tag(version)
    if normalized_tag != expected_tag:
        raise ValueError(
            f"Release tag {normalized_tag!r} does not match project version {version!r}. "
            f"Expected {expected_tag!r}."
        )

    return normalized_tag


def ensure_clean_worktree(repo_root: Path) -> None:
    """Require a clean Git worktree before releasing."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "git status failed"
        raise RuntimeError(f"Unable to inspect Git worktree state: {detail}")

    if result.stdout.strip():
        raise RuntimeError(
            "Git worktree is not clean. Commit, stash, or pass "
            "--skip-clean-tree-check to override."
        )


def run_command(command: list[str], cwd: Path) -> None:
    """Run a subprocess and raise a structured error on failure."""
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        rendered = " ".join(command)
        detail = (result.stderr or result.stdout).strip()
        if detail:
            raise RuntimeError(
                f"Command failed with exit code {result.returncode}: {rendered}\n{detail}"
            )
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {rendered}")


def build_command(package_root: Path) -> tuple[list[str], Path]:
    """Return the isolated build invocation and working directory.

    Running from the parent directory avoids local ``build/`` folders inside the
    repository shadowing the third-party ``build`` module.
    """
    return [sys.executable, "-m", "build", str(package_root)], package_root.parent


def twine_check_command(artifacts: Iterable[Path], package_root: Path) -> tuple[list[str], Path]:
    """Return the twine check invocation and a cwd outside the repository root."""
    return [sys.executable, "-m", "twine", "check", *[str(path) for path in artifacts]], package_root.parent


def resolve_dist_dir(pyproject_path: Path, requested_dist_dir: str) -> Path:
    """Resolve the dist directory, keeping custom pyproject paths internally consistent."""
    dist_dir = Path(requested_dist_dir).resolve()
    if dist_dir == DEFAULT_DIST_DIR and pyproject_path != DEFAULT_PYPROJECT:
        return pyproject_path.parent / "dist"
    return dist_dir


def collect_dist_artifacts(dist_dir: Path) -> list[Path]:
    """Collect built distribution artifacts from ``dist/``."""
    if not dist_dir.is_dir():
        raise FileNotFoundError(f"Distribution directory not found: {dist_dir}")

    artifacts = sorted(path for path in dist_dir.iterdir() if path.is_file())
    if not artifacts:
        raise FileNotFoundError(f"No distribution artifacts found in: {dist_dir}")

    return artifacts


def npm_package_exists(npm_package_dir: Path) -> bool:
    """Return True when an in-repo npm package surface is present."""
    return (npm_package_dir / "package.json").is_file()


def load_npm_package_metadata(npm_package_dir: Path) -> tuple[str, str]:
    """Load the in-repo npm package name and version from ``package.json``."""
    package_json = npm_package_dir / "package.json"
    if not package_json.is_file():
        raise FileNotFoundError(f"npm package.json not found: {package_json}")

    payload = json.loads(package_json.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid package.json payload in {package_json}")

    name = payload.get("name")
    version = payload.get("version")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Missing package name in {package_json}")
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"Missing package version in {package_json}")

    return name.strip(), version.strip()


def validate_npm_package(npm_package_dir: Path) -> None:
    """Require the in-repo npm package to build and pack locally when requested."""
    if not npm_package_exists(npm_package_dir):
        raise FileNotFoundError(f"npm package.json not found: {npm_package_dir / 'package.json'}")

    load_npm_package_metadata(npm_package_dir)
    run_command(["npm", "ci"], npm_package_dir)
    run_command(["npm", "run", "build"], npm_package_dir)
    run_command(["npm", "pack", "--dry-run"], npm_package_dir)


def validate_dist_artifacts(name: str, version: str, artifacts: Iterable[Path]) -> None:
    """Require a wheel and sdist matching the normalized project name and version."""
    normalized_name = normalize_artifact_stem(name)
    expected_wheel_prefix = f"{normalized_name}-{version}-"
    expected_sdist_prefix = f"{normalized_name}-{version}"

    wheel_found = False
    sdist_found = False

    for artifact in artifacts:
        filename = artifact.name
        if filename.startswith(expected_wheel_prefix) and filename.endswith(".whl"):
            wheel_found = True
        if filename.startswith(expected_sdist_prefix) and filename.endswith((".tar.gz", ".zip")):
            sdist_found = True

    if not wheel_found:
        raise FileNotFoundError(
            "No wheel artifact matched the expected public package name "
            f"{expected_wheel_prefix}*.whl."
        )
    if not sdist_found:
        raise FileNotFoundError(
            "No source distribution artifact matched the expected public package name "
            f"{expected_sdist_prefix}.tar.gz or .zip."
        )


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for release preflight checks."""
    parser = argparse.ArgumentParser(description="Run release preflight checks for cortex-persist.")
    parser.add_argument(
        "--tag",
        help="Release Git tag to validate, for example v0.3.0b2.",
    )
    parser.add_argument(
        "--pyproject",
        default=str(DEFAULT_PYPROJECT),
        help="Path to the pyproject.toml file to validate.",
    )
    parser.add_argument(
        "--dist-dir",
        default=str(DEFAULT_DIST_DIR),
        help="Directory where build artifacts should exist.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip `python -m build` and validate existing dist artifacts only.",
    )
    parser.add_argument(
        "--skip-twine-check",
        action="store_true",
        help="Skip `python -m twine check` for built artifacts.",
    )
    parser.add_argument(
        "--skip-clean-tree-check",
        action="store_true",
        help="Allow running release checks with a dirty Git worktree.",
    )
    parser.add_argument(
        "--check-npm-readiness",
        action="store_true",
        help="Also validate the in-repo npm package with install, build, and dry-run pack.",
    )
    parser.add_argument(
        "--npm-package-dir",
        default=str(DEFAULT_NPM_PACKAGE_DIR),
        help="Path to the in-repo npm package directory.",
    )
    return parser


def main() -> int:
    """Run the release preflight command."""
    parser = build_parser()
    args = parser.parse_args()

    pyproject_path = Path(args.pyproject).resolve()
    package_root = pyproject_path.parent
    dist_dir = resolve_dist_dir(pyproject_path, args.dist_dir)
    npm_package_dir = Path(args.npm_package_dir).resolve()

    try:
        name, version = load_project_metadata(pyproject_path)
        print(f"[release-preflight] package={name} version={version}")

        if args.tag:
            normalized_tag = validate_release_tag(version, args.tag)
            print(f"[release-preflight] tag={normalized_tag} matches version")

        if not args.skip_clean_tree_check:
            ensure_clean_worktree(package_root)
            print("[release-preflight] worktree is clean")

        if not args.skip_build:
            command, cwd = build_command(package_root)
            run_command(command, cwd)

        artifacts = collect_dist_artifacts(dist_dir)
        validate_dist_artifacts(name, version, artifacts)
        print(f"[release-preflight] artifacts={len(artifacts)} in {dist_dir}")

        if not args.skip_twine_check:
            command, cwd = twine_check_command(artifacts, package_root)
            run_command(command, cwd)

        if args.check_npm_readiness:
            package_name, package_version = load_npm_package_metadata(npm_package_dir)
            validate_npm_package(npm_package_dir)
            print(
                "[release-preflight] npm-package="
                f"{package_name}@{package_version} build+pack OK"
            )

    except (FileNotFoundError, RuntimeError, ValueError) as err:
        print(f"[release-preflight] FAIL: {err}", file=sys.stderr)
        return 1

    print("[release-preflight] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
