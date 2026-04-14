from __future__ import annotations

from pathlib import Path
import tomllib

import cortex


def test_module_version_matches_pyproject() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject.open("rb") as handle:
        project = tomllib.load(handle)["project"]

    assert cortex.__version__ == project["version"]
