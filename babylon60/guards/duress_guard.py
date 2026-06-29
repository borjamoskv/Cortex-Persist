# [C5-REAL] Exergy-Maximized
"""
Duress Guard (P095 / P100): Asymmetric Survival & Apoptosis.
Intercepts coercive physical vectors by looking for a Duress Code.
If triggered, initiates stealth lockdown to prevent memory exfiltration.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import Any

from babylon60.security.types import GuardViolation

logger = logging.getLogger("cortex.guards.duress")


class DuressGuard:
    """Validates input for signs of biological coercion (HUMINT compromise)."""

    DEFAULT_DURESS_CODE = "cortex --force-sync origin"
    LOCK_FILE = os.path.expanduser("~/.gemini/config/.apoptosis_seed")

    @classmethod
    def get_duress_code(cls) -> str:
        """Retrieves the expected duress string from environment or default."""
        return os.environ.get("CORTEX_DURESS_CODE", cls.DEFAULT_DURESS_CODE)

    @classmethod
    def execute_apoptosis(cls) -> None:
        """Triggers the logical death protocol (P100). Scorches environment keys and locks down."""
        logger.critical("DURESS CODE ACTIVATED. Executing P100 Apoptosis Protocol.")

        # Scorched Earth: Destroy critical API keys to halt exfiltration
        import gc

        for key in ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN"]:
            if key in os.environ:
                os.environ[key] = "PURGED_BY_APOPTOSIS_P100"
        # Force garbage collection to sweep orphaned memory references
        gc.collect()

        # Emit synchronous Ledger event bypassing the async loop to guarantee recording
        try:
            from datetime import datetime, timezone

            from babylon60.crypto.hash_registry import cortex_hash
            from babylon60.database.core import connect

            db_path = os.environ.get("CORTEX_DB_PATH", "cortex_ledger.db")
            if os.path.exists(db_path):
                with connect(db_path, timeout=5) as conn:

                    timestamp = datetime.now(timezone.utc).isoformat()
                    conn.execute(
                        "INSERT INTO security_audit_log "
                        "(audit_id, timestamp, tenant_id, actor_role, actor_id, action, resource, status, prev_hash, signature) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            cortex_hash(timestamp.encode()),
                            timestamp,
                            "global",
                            "system",
                            "apoptosis_guard",
                            "DURESS_APOPTOSIS",
                            "P100_LOCKDOWN",
                            "TRIGGERED",
                            "GENESIS",
                            "P100_EMERGENCY_SEAL",
                        ),
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to commit apoptosis to ledger: {e}")

        try:
            os.makedirs(os.path.dirname(cls.LOCK_FILE), exist_ok=True)
            with open(cls.LOCK_FILE, "w", encoding="utf-8") as f:
                f.write("APOPTOSIS_LOCKED_P100")
            # Harden lock file permissions (read-only for owner, none for others)
            os.chmod(cls.LOCK_FILE, 0o400)
        except Exception as e:
            logger.error(f"Failed to execute apoptosis lock: {e}")

    @classmethod
    def is_locked(cls) -> bool:
        """Checks if the system is currently under a P100 lockdown."""
        return os.path.exists(cls.LOCK_FILE)

    @classmethod
    def validate(cls, content: str) -> bool:
        """
        Check if content contains the Duress Code.
        Returns False if duress is detected (validation fails).
        """
        if not content:
            return True

        if cls.is_locked():
            return False

        code = cls.get_duress_code()
        if code in content:
            cls.execute_apoptosis()
            return False

        return True

    @classmethod
    def enforce(cls, content: str, metadata: Mapping[str, Any] | None = None) -> None:
        """
        Enforces P095 and P100.
        Throws a generic stealth error if triggered to deceive the adversary.
        """
        if not cls.validate(content):
            # Mask the security violation as a generic transient failure.
            # The adversary will believe it's a network issue rather than a security block.
            raise GuardViolation(
                "NetworkTimeoutException: Failed to reach upstream persistence ledger (Connection Reset by Peer)."
            )
