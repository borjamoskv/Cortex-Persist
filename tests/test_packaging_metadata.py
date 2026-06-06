# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from pathlib import Path

import tomllib


def _dependency_names(values: list[str]) -> set[str]:
    names: set[str] = set()
    for value in values:
        name = value.split(";", 1)[0].strip().split("[", 1)[0].split(">=", 1)[0].split("==", 1)[0]
        names.add(name)
    return names


def test_heavy_dependencies_live_in_optional_extras() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
        project = data["project"]

    base_dependencies = _dependency_names(project["dependencies"])
    extras = project["optional-dependencies"]

    assert "sentence-transformers" not in base_dependencies
    assert "onnxruntime" not in base_dependencies
    assert "chromadb" not in base_dependencies
    assert "numba" not in base_dependencies
    assert "aiohttp" not in base_dependencies
    assert "beautifulsoup4" not in base_dependencies
    assert "arq" not in base_dependencies
    assert "email-validator" not in base_dependencies
    assert "PyYAML" not in base_dependencies
    assert "watchdog" not in base_dependencies
    assert "aiofiles" not in base_dependencies
    assert "pyobjc-core" not in base_dependencies
    assert "pyobjc-framework-Cocoa" not in base_dependencies

    assert _dependency_names(extras["embeddings"]) == {
        "sentence-transformers",
        "onnxruntime",
        "optimum",
    }
    assert _dependency_names(extras["knowledge"]) == {"chromadb"}
    assert _dependency_names(extras["acceleration"]) == {"numba"}
    assert _dependency_names(extras["api"]) >= {
        "fastapi",
        "uvicorn",
        "httpx",
        "sse-starlette",
        "email-validator",
    }
    assert _dependency_names(extras["mcp"]) == {
        "mcp",
        "aiohttp",
        "beautifulsoup4",
        "markdownify",
        "watchdog",
    }
    assert _dependency_names(extras["daemon"]) == {"aiofiles", "aiohttp", "arq", "watchdog"}
    assert _dependency_names(extras["platform"]) >= {"pyobjc-core", "pyobjc-framework-Cocoa"}
    assert _dependency_names(extras["authoring"]) == {"PyYAML"}
    assert extras["all"] == [
        "cortex-persist[compute,secure,api,mcp,daemon,platform,authoring,dev,adk,toolbox,billing,cloud,trends,embeddings,knowledge,acceleration]"
    ]

    assert (
        Path(__file__).resolve().parents[1] / "cortex" / "cli" / "assets" / "tips.json"
    ).exists()
