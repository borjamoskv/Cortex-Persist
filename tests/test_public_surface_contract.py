from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_public_docs_do_not_reference_known_broken_docs_urls() -> None:
    banned = (
        "https://cortexpersist.com/docs/system-map",
        "https://cortexpersist.com/docs/cortex-native-technologies",
        "https://cortexpersist.com/docs/api",
        "https://cortexpersist.com/docs/security_trust_model",
        "https://cortexpersist.com/docs/operations",
        "https://cortexpersist.com/docs/cross_platform_guide",
    )
    paths = (
        "README.md",
        "README.es.md",
        "README.zh.md",
        "ENTERPRISE_READINESS.md",
        "SUPPORT.md",
        "DUE_DILIGENCE_CHECKLIST.md",
        "DEPLOYMENT_HARDENING.md",
        "docs/documentation-boundary.md",
        "docs/AXIOMS.md",
        "docs/CONTRIBUTING.md",
        "docs/OPERATIONS.md",
        "docs/SECURITY_TRUST_MODEL.md",
        "docs/api.md",
        "docs/architecture.md",
        "docs/system-map.md",
        "docs/cortex-native-technologies.md",
        "sdks/python/README.md",
        "sdks/js/README.md",
    )

    for path in paths:
        content = _read(path)
        for url in banned:
            assert url not in content, f"{path} still references broken URL: {url}"


def test_readmes_and_examples_use_public_python_import_surface() -> None:
    expected = "from cortex_persist import "
    for path in (
        "README.md",
        "README.es.md",
        "README.zh.md",
        "docs/api.md",
        "sdks/python/README.md",
        "examples/quickstart.py",
    ):
        assert expected in _read(path), f"{path} should demonstrate the public cortex_persist import"


def test_docs_pages_are_no_longer_redirect_only_shims() -> None:
    shim_markers = (
        "This file exists as a stable GitHub-facing path",
        "The canonical long-form document now lives at:",
        "The canonical long-form contributor guide now lives at:",
        "The canonical long-form operations document now lives at:",
        "The canonical long-form architecture document now lives at:",
    )
    for path in (
        "docs/AXIOMS.md",
        "docs/CONTRIBUTING.md",
        "docs/OPERATIONS.md",
        "docs/SECURITY_TRUST_MODEL.md",
        "docs/api.md",
        "docs/architecture.md",
    ):
        content = _read(path)
        for marker in shim_markers:
            assert marker not in content, f"{path} is still acting like a redirect shim"


def test_sdk_and_docs_match_current_distribution_story() -> None:
    assert "npm install ./sdks/js" in _read("sdks/js/README.md")
    assert "not live yet" in _read("sdks/js/README.md")
    assert "pip install ." in _read("sdks/python/README.md")
    assert "source installation from this repository" in _read("README.md")


def test_buyer_facing_docs_use_current_supported_verification_flow() -> None:
    for path in (
        "README.md",
        "README.es.md",
        "README.zh.md",
        "docs/api.md",
        "docs/canonical-demo.md",
        "DUE_DILIGENCE_CHECKLIST.md",
        "DEPLOYMENT_HARDENING.md",
    ):
        content = _read(path)
        assert "cortex trust-ledger verify --full" in content, (
            f"{path} should show the full ledger verification command"
        )
        assert "cortex compliance-report" not in content, (
            f"{path} should not present compliance-report as the primary buyer-facing flow"
        )


def test_support_and_governance_point_to_supported_core_boundary() -> None:
    assert "docs/supported-core.md" in _read("SUPPORT.md")
    assert "docs/supported-core.md" in _read("REPO_GOVERNANCE.md")


def test_pyproject_all_extra_is_not_self_referential() -> None:
    pyproject = _read("pyproject.toml")
    assert 'cortex-persist[api,dev,adk,toolbox,billing,cloud,trends]' not in pyproject


def test_supported_core_page_keeps_current_public_contract() -> None:
    content = _read("docs/supported-core.md")

    assert "Public package publication | Not yet part of the supported contract" in content
    assert "API posture | Self-hosted from source, beta" in content
    assert "pip install cortex-persist" in content
    assert "npm install @cortex-persist/sdk" in content
    for command in (
        "cortex init",
        "cortex store",
        "cortex recall",
        "cortex search",
        "cortex verify",
        "cortex trust-ledger verify --full",
        "cortex export",
        "cortex status",
    ):
        assert command in content
    for excluded_surface in (
        "Public PyPI installation such as `pip install cortex-persist`",
        "Public npm installation such as `npm install @cortex-persist/sdk`",
        "Managed cloud distribution",
    ):
        assert excluded_surface in content


def test_canonical_demo_keeps_tamper_then_export_flow() -> None:
    content = _read("docs/canonical-demo.md")

    assert "## Tamper Drill" in content
    for step in (
        "cortex recall risk-bot --db \"$DB\"",
        "cortex verify \"$FACT_ID\" --db \"$DB\"",
        "cortex trust-ledger verify --full --db \"$DB\"",
        "UPDATE facts SET content = ? WHERE id = ?",
        "INTEGRITY VIOLATION",
        "Ledger is COMPROMISED",
        'cortex export --project risk-bot --format json --out "$OUT" --db "$DB"',
    ):
        assert step in content
    assert content.index("## Tamper Drill") < content.index('cortex export --project risk-bot')
    assert content.index("UPDATE facts SET content = ? WHERE id = ?") < content.index(
        'cortex export --project risk-bot --format json --out "$OUT" --db "$DB"'
    )


def test_api_beta_install_contract_is_explicit_across_examples_and_sdks() -> None:
    for path in (
        "docs/api.md",
        "sdks/python/README.md",
        "sdks/js/README.md",
        "examples/quickstart.py",
        "examples/quickstart.js",
    ):
        assert 'pip install -e ".[api]"' in _read(path), (
            f"{path} should make the beta API install contract explicit"
        )


def test_api_and_operations_docs_keep_optional_beta_language() -> None:
    api_doc = _read("docs/api.md")
    operations_doc = _read("docs/OPERATIONS.md")

    assert "optional self-hosted beta surface" in api_doc
    assert "## Beta API Endpoints" in api_doc
    assert "Experimental / outside supported core" in operations_doc


def test_support_and_enterprise_docs_keep_supported_core_first() -> None:
    support_doc = _read("SUPPORT.md")
    enterprise_doc = _read("ENTERPRISE_READINESS.md")

    assert "The support boundary starts with [docs/supported-core.md]" in support_doc
    assert "supported CLI core and the documented beta API surface" in support_doc
    assert "**Supported core boundary:** [docs/supported-core.md]" in enterprise_doc
    assert "**Canonical product proof:** [docs/canonical-demo.md]" in enterprise_doc
    assert "**Optional beta API surface:** [docs/api.md]" in enterprise_doc


def test_architecture_and_trust_docs_mark_broader_repo_surfaces_explicitly() -> None:
    architecture_doc = _read("docs/architecture.md")
    trust_doc = _read("docs/SECURITY_TRUST_MODEL.md")

    assert "Broader repo surface, not supported core" in architecture_doc
    assert "Today, the supported operator path is the local-first CLI core." in architecture_doc
    assert "The current supported operator path is the local-first CLI core." in trust_doc
    assert "self-hosted beta API and the MCP server use the same trust concepts" in trust_doc


def test_local_docs_entrypoints_exist_for_public_navigation() -> None:
    for path in (
        "docs/system-map.md",
        "docs/cortex-native-technologies.md",
        "docs/api.md",
        "docs/SECURITY_TRUST_MODEL.md",
        "docs/OPERATIONS.md",
        "docs/architecture.md",
    ):
        assert (REPO_ROOT / path).is_file(), f"Missing expected public docs page: {path}"
