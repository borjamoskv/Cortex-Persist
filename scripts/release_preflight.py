"""Validate release artifacts before publication.

This script checks the built wheel and sdist for:
- expected package naming
- required metadata files
- absence of forbidden repository surfaces in public artifacts
- absence of duplicate root package distribution names in subpackages
"""

from __future__ import annotations

import argparse
import re
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
PROJECT_NAME_RE = re.compile(r"(?m)^name\s*=\s*['\"]([^'\"]+)['\"]")


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


def read_project_name(pyproject_path: Path) -> str | None:
    """Return the first PEP 621 project.name found in a pyproject file.

    This intentionally stays lightweight so the release preflight has no
    runtime dependency on Python 3.11's tomllib or third-party TOML parsers.
    """
    text = pyproject_path.read_text(encoding="utf-8")
    match = PROJECT_NAME_RE.search(text)
    return match.group(1) if match else None


def validate_unique_distribution_name(repo_root: Path, package_name: str) -> None:
    """Ensure only the repository root claims the canonical distribution name."""
    root_pyproject = repo_root / "pyproject.toml"
    if not root_pyproject.exists():
        fail("root pyproject.toml is missing")

    root_name = read_project_name(root_pyproject)
    if root_name != package_name:
        fail(
            f"root pyproject.toml project.name={root_name!r} does not match "
            f"expected package {package_name!r}"
        )

    offenders: list[str] = []
    for pyproject_path in sorted(repo_root.rglob("pyproject.toml")):
        if pyproject_path == root_pyproject:
            continue
        project_name = read_project_name(pyproject_path)
        if project_name == package_name:
            offenders.append(str(pyproject_path.relative_to(repo_root)))

    if offenders:
        offender_list = ", ".join(offenders)
        fail(
            f"duplicate distribution name {package_name!r} found outside root: "
            f"{offender_list}. Use a distinct package name such as "
            "'cortex-persist-cloud', or remove the nested pyproject until ready."
        )


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
    repo_root = Path.cwd()
    validate_unique_distribution_name(repo_root, args.package_name)

    dist_dir = Path(args.dist)
    if not dist_dir.is_dir():
        fail(f"dist directory {dist_dir} does not exist")

    artifacts = discover_artifacts(dist_dir, args.package_name)
    validate_wheel(artifacts.wheel)
    validate_sdist(artifacts.sdist)
    print(f"release-preflight: OK for {artifacts.wheel.name} and {artifacts.sdist.name}")


if __name__ == "__main__":
    main()
