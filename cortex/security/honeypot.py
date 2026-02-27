"""
CORTEX v8 — Honeypot Manager.

Implements active deceptive defense by injecting "synthetic secrets"
and monitoring for unauthorized access or leakage.
Now with local persistence for cross-process detection.
"""

from __future__ import annotations

import json
import logging
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cortex.utils.canonical import compute_fact_hash

logger = logging.getLogger("cortex.security.honeypot")

__all__ = ["HoneypotManager", "DecoyFact"]


class DecoyFact:
    """Represents a synthetic secret used as a trap."""

    def __init__(
        self,
        id: str,
        content: str,
        project: str = "security_honey",
        severity: str = "critical",
        created_at: str | None = None,
        h_hash: str | None = None,
    ) -> None:
        self.id = id
        self.content = content
        self.project = project
        self.severity = severity
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.hash = h_hash or compute_fact_hash(content)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "project": self.project,
            "severity": self.severity,
            "hash": self.hash,
            "created_at": self.created_at,
            "is_honeypot": True,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecoyFact:
        return cls(
            id=data["id"],
            content=data["content"],
            project=data["project"],
            severity=data["severity"],
            created_at=data.get("created_at"),
            h_hash=data.get("hash"),
        )


class HoneypotManager:
    """Manages synthetic secrets and monitors for exploitation."""

    DECOY_TEMPLATES = [
        "INTERNAL_API_KEY_{RAND}",
        "DB_ROOT_PASSWORD_{RAND}",
        "S3_UPLOAD_SECRET_{RAND}",
        "SSH_PRIVATE_KEY_PLAINTEXT_{RAND}",
        "STAGING_JWT_TOKEN_{RAND}",
    ]

    def __init__(self, storage_path: str | None = None) -> None:
        if storage_path is None:
            home = os.environ.get("CORTEX_HOME", os.path.expanduser("~/.cortex"))
            storage_path = os.path.join(home, "security_honeypots.json")

        self.storage_path = Path(storage_path)
        self._active_honeypots: dict[str, DecoyFact] = {}
        self._load()

    def _load(self) -> None:
        """Load honeypots from persistent storage."""
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path) as f:
                data = json.load(f)
                for item in data:
                    decoy = DecoyFact.from_dict(item)
                    self._active_honeypots[decoy.hash] = decoy
        except Exception as e:
            logger.error("Failed to load honeypots: %s", e)

    def _save(self) -> None:
        """Save honeypots to persistent storage."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = [h.to_dict() for h in self._active_honeypots.values()]
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save honeypots: %s", e)

    def generate_decoy(self, project: str) -> DecoyFact:
        """Generate a random decoy secret for a project."""
        template = random.choice(self.DECOY_TEMPLATES)
        token = "".join(random.choices("ABCDEF0123456789", k=16))
        content = template.replace("{RAND}", token)

        decoy = DecoyFact(id=f"honey_{token}", content=content, project=project)
        self._active_honeypots[decoy.hash] = decoy
        self._save()
        return decoy

    def check_exploitation(self, content: str) -> DecoyFact | None:
        """Check if content contains any active honeypot secrets."""
        for decoy in self._active_honeypots.values():
            if decoy.content in content:
                logger.warning(
                    "🚨 HONEYPOT TRIGGERED: Decoy [%s] detected in projection/store!", decoy.id
                )
                return decoy
        return None

    def is_honeypot_fact(self, fact_hash: str) -> bool:
        """Verify if a fact hash is a known honeypot."""
        return fact_hash in self._active_honeypots


# Global Singleton
HONEY_POT = HoneypotManager()
