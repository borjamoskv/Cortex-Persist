"""Privacy mixin — Zero-Trust Privacy Shield and classification."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("cortex.privacy")


class PrivacyMixin:
    """Zero-Trust Privacy Shield logic for data storage."""

    @staticmethod
    def _apply_privacy_shield(
        content: str, project: str, meta: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Zero-Trust Privacy Shield — classify content before storage.

        If sensitive patterns (API keys, private keys, connection strings)
        are detected, inject privacy metadata into the fact for audit trail.
        Degrades gracefully if classifier is not available.
        """
        try:
            from cortex.storage.classifier import classify_content

            sensitivity = classify_content(content)
            if sensitivity.is_sensitive:
                logger.warning(
                    "PRIVACY SHIELD: Sensitive patterns detected (%s) in project [%s]. "
                    "Fact flagged for audit.",
                    ", ".join(sensitivity.matches),
                    project,
                )
                privacy_meta = {
                    "privacy_flagged": True,
                    "privacy_matches": sensitivity.matches,
                    "privacy_score": sensitivity.score,
                }
                return {**(meta or {}), **privacy_meta}
        except ImportError:
            pass  # Classifier not available — degrade gracefully
        return meta
