from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "release_preflight.py"


def _load_release_preflight_module():
    spec = importlib.util.spec_from_file_location("release_preflight", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validate_release_tag_accepts_matching_version() -> None:
    module = _load_release_preflight_module()

    assert module.validate_release_tag("0.3.0b2", "v0.3.0b2") == "v0.3.0b2"


def test_validate_release_tag_rejects_mismatch() -> None:
    module = _load_release_preflight_module()

    try:
        module.validate_release_tag("0.3.0b2", "v0.3.0b1")
    except ValueError as err:
        assert "does not match" in str(err)
    else:
        raise AssertionError("Expected validate_release_tag to reject mismatched tags")


def test_release_preflight_cli_succeeds_when_expensive_checks_are_skipped() -> None:
    module = _load_release_preflight_module()
    _, version = module.load_project_metadata(module.DEFAULT_PYPROJECT)
    tag = module.expected_release_tag(version)
    with tempfile.TemporaryDirectory(prefix="cortex-release-preflight-") as tmpdir:
        dist_dir = Path(tmpdir)
        (dist_dir / f"cortex_persist-{version}-py3-none-any.whl").write_text(
            "placeholder wheel",
            encoding="utf-8",
        )
        (dist_dir / f"cortex_persist-{version}.tar.gz").write_text(
            "placeholder sdist",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--tag",
                tag,
                "--dist-dir",
                str(dist_dir),
                "--skip-build",
                "--skip-twine-check",
                "--skip-clean-tree-check",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0
    assert "[release-preflight] OK" in result.stdout


def test_release_preflight_cli_fails_for_mismatched_tag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--tag",
            "v0.0.0",
            "--skip-build",
            "--skip-twine-check",
            "--skip-clean-tree-check",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "[release-preflight] FAIL" in result.stderr


def test_validate_dist_artifacts_requires_matching_wheel_and_sdist() -> None:
    module = _load_release_preflight_module()
    artifacts = [
        Path("cortex_persist-0.3.0b2-py3-none-any.whl"),
        Path("cortex_persist-0.3.0b2.tar.gz"),
    ]

    module.validate_dist_artifacts("cortex-persist", "0.3.0b2", artifacts)


def test_validate_dist_artifacts_rejects_missing_sdist() -> None:
    module = _load_release_preflight_module()
    artifacts = [Path("cortex_persist-0.3.0b2-py3-none-any.whl")]

    try:
        module.validate_dist_artifacts("cortex-persist", "0.3.0b2", artifacts)
    except FileNotFoundError as err:
        assert "source distribution" in str(err)
    else:
        raise AssertionError("Expected validate_dist_artifacts to require an sdist")


def test_normalize_artifact_stem_rewrites_distribution_name() -> None:
    module = _load_release_preflight_module()

    assert module.normalize_artifact_stem("cortex-persist") == "cortex_persist"


def test_build_command_runs_from_repo_parent_to_avoid_local_shadowing() -> None:
    module = _load_release_preflight_module()

    command, cwd = module.build_command(Path("/tmp/Cortex-Persist"))

    assert command == [sys.executable, "-m", "build", "/tmp/Cortex-Persist"]
    assert cwd == Path("/tmp")


def test_resolve_dist_dir_tracks_custom_pyproject_root() -> None:
    module = _load_release_preflight_module()

    resolved = module.resolve_dist_dir(
        Path("/tmp/custom-package/pyproject.toml"),
        str(module.DEFAULT_DIST_DIR),
    )

    assert resolved == Path("/tmp/custom-package/dist")


def test_load_npm_package_metadata_reads_name_and_version() -> None:
    module = _load_release_preflight_module()

    name, version = module.load_npm_package_metadata(module.DEFAULT_NPM_PACKAGE_DIR)

    assert name == "@cortex-persist/sdk"
    assert version


def test_release_preflight_keeps_npm_readiness_opt_in() -> None:
    module = _load_release_preflight_module()
    parser = module.build_parser()

    args = parser.parse_args([])

    assert args.check_npm_readiness is False


def test_release_preflight_cli_ignores_bad_npm_dir_unless_opted_in() -> None:
    module = _load_release_preflight_module()
    _, version = module.load_project_metadata(module.DEFAULT_PYPROJECT)
    tag = module.expected_release_tag(version)
    with tempfile.TemporaryDirectory(prefix="cortex-release-preflight-") as tmpdir:
        dist_dir = Path(tmpdir)
        (dist_dir / f"cortex_persist-{version}-py3-none-any.whl").write_text(
            "placeholder wheel",
            encoding="utf-8",
        )
        (dist_dir / f"cortex_persist-{version}.tar.gz").write_text(
            "placeholder sdist",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--tag",
                tag,
                "--dist-dir",
                str(dist_dir),
                "--npm-package-dir",
                str(dist_dir / "missing-js-sdk"),
                "--skip-build",
                "--skip-twine-check",
                "--skip-clean-tree-check",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0
    assert "[release-preflight] OK" in result.stdout


def test_release_preflight_cli_fails_when_explicit_npm_readiness_is_broken() -> None:
    module = _load_release_preflight_module()
    _, version = module.load_project_metadata(module.DEFAULT_PYPROJECT)
    tag = module.expected_release_tag(version)
    with tempfile.TemporaryDirectory(prefix="cortex-release-preflight-") as tmpdir:
        dist_dir = Path(tmpdir)
        (dist_dir / f"cortex_persist-{version}-py3-none-any.whl").write_text(
            "placeholder wheel",
            encoding="utf-8",
        )
        (dist_dir / f"cortex_persist-{version}.tar.gz").write_text(
            "placeholder sdist",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--tag",
                tag,
                "--dist-dir",
                str(dist_dir),
                "--npm-package-dir",
                str(dist_dir / "missing-js-sdk"),
                "--check-npm-readiness",
                "--skip-build",
                "--skip-twine-check",
                "--skip-clean-tree-check",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 1
    assert "npm package.json not found" in result.stderr
