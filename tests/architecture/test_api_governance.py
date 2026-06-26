# [C5-REAL] Exergy-Maximized
"""
Governance Test: API Surface Canonical Invariants

Enforces ADR-0003. This test guarantees that `cortex.api.core` remains the
declared canonical API surface and that the legacy `api.server` module
retains its deprecation banner. If any of these invariants break, the
architectural governance has been violated.
"""

import importlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestAPIGovernance:
    """Structural invariants for API surface governance (ADR-0003)."""

    def test_canonical_module_exists(self) -> None:
        """cortex.api.core must exist and be importable."""
        spec = importlib.util.find_spec("cortex.api.core")
        assert spec is not None, (
            "cortex.api.core is not importable. "
            "The canonical API surface has been removed or renamed. "
            "This violates ADR-0003."
        )

    def test_canonical_module_exposes_app(self) -> None:
        """cortex.api.core must expose a FastAPI `app` instance."""
        core = importlib.import_module("cortex.api.core")
        assert hasattr(core, "app"), (
            "cortex.api.core does not expose an `app` attribute. "
            "The canonical entrypoint has been broken."
        )

    def test_governance_document_exists(self) -> None:
        """The API surfaces governance doc must exist."""
        gov_doc = REPO_ROOT / "docs" / "architecture" / "api-surfaces.md"
        assert gov_doc.exists(), (
            f"Governance document missing: {gov_doc}. "
            "The architectural source of truth for API surfaces has been deleted."
        )

    def test_adr_0003_exists(self) -> None:
        """ADR-0003 (canonical API surface) must exist."""
        adr = REPO_ROOT / "docs" / "architecture" / "adr" / "0003-canonical-api-surface.md"
        assert adr.exists(), (
            f"ADR-0003 missing: {adr}. "
            "The formal architecture decision record for the canonical API has been deleted."
        )

    def test_legacy_server_has_deprecation_warning(self) -> None:
        """If api/server.py still exists, it must contain a DeprecationWarning."""
        legacy = REPO_ROOT / "api" / "server.py"
        if not legacy.exists():
            # Legacy module already removed — governance satisfied.
            return
        source = legacy.read_text(encoding="utf-8")
        assert "DeprecationWarning" in source, (
            "api/server.py exists but does not contain a DeprecationWarning. "
            "The deprecation banner has been removed, violating ADR-0003."
        )

    def test_governance_doc_declares_canonical_surface(self) -> None:
        """The governance doc must declare cortex.api.core as canonical."""
        gov_doc = REPO_ROOT / "docs" / "architecture" / "api-surfaces.md"
        if not gov_doc.exists():
            return  # Covered by test_governance_document_exists
        content = gov_doc.read_text(encoding="utf-8")
        assert re.search(r"cortex\.api\.core", content), (
            "Governance document does not declare cortex.api.core as the canonical surface."
        )
        assert re.search(r"(?i)canonical|source of truth", content), (
            "Governance document does not use 'canonical' or 'source of truth' terminology."
        )
