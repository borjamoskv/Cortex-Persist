"""Validate release artifacts before publication.

This script checks the built wheel and sdist for:
- expected package naming
- required metadata files
- absence of forbidden repository surfaces in public artifacts
"""

from __future__ import annotations

import argparse
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PACKAGE = "cortex-persist"
FORBIDDEN_SEGMENTS = (
    "cortex-sdk/",
    "sdks/",
    ".github/",
    "node_modules/",
    "docs_backup/",
    "worktrees/",
)
REQUIRED_WHEEL_PREFIXES = ("cortex/",)
REQUIRED_SDIST_SUFFIXES = ("README.md", "pyproject.toml", "LICENSE")


@dataclass(frozen=True)
class ArtifactSet:
    wheel: Path
    sdist: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", default="dist", help="Directory containing built artifacts.")
    parser.add_argument(
        "--package-name",
        default=DEFAULT_PACKAGE,
        help="Expected published package name.",
    )
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"release-preflight: {message}", file=sys.stderr)
    raise SystemExit(1)


def normalized_package_name(package_name: str) -> str:
    return package_name.replace("-", "_")


def discover_artifacts(dist_dir: Path, package_name: str) -> ArtifactSet:
    normalized = normalized_package_name(package_name)
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))

    if len(wheels) != 1 or len(sdists) != 1:
        fail(
            f"expected exactly one wheel and one sdist in {dist_dir}, "
            f"found {len(wheels)} wheel(s) and {len(sdists)} sdist(s)"
        )

    wheel = wheels[0]
    sdist = sdists[0]

    if not wheel.name.startswith(f"{normalized}-"):
        fail(f"wheel name {wheel.name!r} does not match expected package {package_name!r}")
    if not sdist.name.startswith(f"{normalized}-"):
        fail(f"sdist name {sdist.name!r} does not match expected package {package_name!r}")

    return ArtifactSet(wheel=wheel, sdist=sdist)


def validate_wheel(wheel_path: Path) -> None:
    with zipfile.ZipFile(wheel_path) as archive:
        names = archive.namelist()

    for segment in FORBIDDEN_SEGMENTS:
        if any(name.startswith(segment) for name in names):
            fail(f"wheel contains forbidden path segment {segment!r}")

    if not any(name.startswith(prefix) for prefix in REQUIRED_WHEEL_PREFIXES for name in names):
        fail(f"wheel is missing required package content under {REQUIRED_WHEEL_PREFIXES!r}")


def validate_sdist(sdist_path: Path) -> None:
    with tarfile.open(sdist_path) as archive:
        names = archive.getnames()

    for segment in FORBIDDEN_SEGMENTS:
        if any(f"/{segment}" in name for name in names):
            fail(f"sdist contains forbidden path segment {segment!r}")

    for suffix in REQUIRED_SDIST_SUFFIXES:
        if not any(name.endswith(suffix) for name in names):
            fail(f"sdist is missing required file ending with {suffix!r}")


def main() -> None:
    args = parse_args()
    dist_dir = Path(args.dist)
    if not dist_dir.is_dir():
        fail(f"dist directory {dist_dir} does not exist")

    artifacts = discover_artifacts(dist_dir, args.package_name)
    validate_wheel(artifacts.wheel)
    validate_sdist(artifacts.sdist)
    print(f"release-preflight: OK for {artifacts.wheel.name} and {artifacts.sdist.name}")


if __name__ == "__main__":
    main()
