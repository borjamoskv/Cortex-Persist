from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_readme_and_package_metadata_point_to_current_docs_surfaces() -> None:
    readme = _read("README.md")
    pyproject = _read("pyproject.toml")

    assert "docs/documentation-boundary.md" in readme
    assert 'Documentation = "https://cortexpersist.com/docs"' in pyproject
    assert "src/content/docs" not in readme


def test_repo_local_docs_pages_no_longer_point_to_internal_docs_tree() -> None:
    doc_paths = [
        "docs/documentation-boundary.md",
        "docs/AXIOMS.md",
        "docs/CONTRIBUTING.md",
        "docs/OPERATIONS.md",
        "docs/SECURITY_TRUST_MODEL.md",
        "docs/api.md",
        "docs/architecture.md",
        "docs/archive.md",
    ]

    for rel_path in doc_paths:
        body = _read(rel_path)
        assert "src/content/docs" not in body


def test_docs_homepage_and_nav_highlight_current_entrypoints() -> None:
    docs_index = _read("docs/index.md")
    mkdocs = _read("mkdocs.yml")

    assert "Run canonical demo" in docs_index
    assert "Review supported core" in docs_index
    assert "Today: source install, local-first runtime, and self-hosted API beta." in docs_index
    assert docs_index.index("<strong>Canonical Demo</strong>") < docs_index.index("<strong>API</strong>")
    assert "optional beta self-hosted REST surface" in docs_index
    assert "Canonical Demo: canonical-demo.md" in mkdocs
    assert "Supported Core: supported-core.md" in mkdocs
