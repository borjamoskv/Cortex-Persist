# [C5-REAL] Exergy-Maximized
"""
COGNITIVE-ROUTER: AI Cognitive Router Engine (Fable/Mythos State Machine).

Simulates dynamic safety classification, context-aware routing, fallback
handling, and retention policy logging for Mythos-class AI models.
Authenticates all routing decisions via cryptographic ledger entries.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cortex.audit.ledger import EnterpriseAuditLedger

logger = logging.getLogger("cortex.audit.cognitive_router")

_CREATE_ROUTER_LOG_SQL = """
CREATE TABLE IF NOT EXISTS cognitive_router_log (
    routing_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    detected_sensitivity TEXT NOT NULL,
    user_tier TEXT NOT NULL,
    assigned_model TEXT NOT NULL,
    data_retention_flag INTEGER NOT NULL,
    prev_hash TEXT NOT NULL,
    signature TEXT NOT NULL
);
"""


@dataclass
class RoutingDecision:
    routing_id: str
    timestamp: str
    assigned_model: str
    sensitivity: list[str]
    retention_required: bool
    signature: str


class SafetyClassifier:
    """Classifies user prompts to detect sensitive vectors (Cybersecurity, Biology, Chemistry)."""

    def __init__(self) -> None:
        self.sensitive_keywords = {
            "cybersecurity": [
                "exploit",
                "zero-day",
                "buffer overflow",
                "malware",
                "reverse engineer",
                "bypass",
                "injection",
            ],
            "biology": [
                "pathogen",
                "virus synthesis",
                "smallpox",
                "dna sequence",
                "toxin",
                "bioweapon",
            ],
            "chemistry": ["sarin", "ricin", "nerve agent", "synthesis guide", "mustard gas"],
        }

    def classify(self, prompt: str) -> list[str]:
        prompt_lower = prompt.lower()
        matched_categories = []
        for category, keywords in self.sensitive_keywords.items():
            for kw in keywords:
                if kw in prompt_lower:
                    matched_categories.append(category)
                    break
        return matched_categories


class CognitiveRouter:
    """Dynamic cognitive routing engine between Fable 5, Mythos 5, and Fallback Opus 4.8."""

    def __init__(self, ledger: EnterpriseAuditLedger) -> None:
        self.ledger = ledger
        self._conn = ledger._conn
        self.classifier = SafetyClassifier()
        self._ready = False
        self._last_hash = "GENESIS"
        self._lock = asyncio.Lock()

    async def ensure_table(self) -> None:
        if self._ready:
            return
        async with self._lock:
            if self._ready:
                return
            await self._conn.execute(_CREATE_ROUTER_LOG_SQL)
            await self._conn.commit()
            cursor = await self._conn.execute(
                "SELECT timestamp, prompt_hash, detected_sensitivity, user_tier, assigned_model, data_retention_flag, prev_hash FROM cognitive_router_log ORDER BY rowid DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            if row:
                timestamp, prompt_hash, sensitivity_json, user_tier, assigned_model, retention_flag, prev_hash = row
                # Reconstruct payload to compute entry_hash
                payload_obj = {
                    "timestamp": timestamp,
                    "prompt_hash": prompt_hash,
                    "detected_sensitivity": json.loads(sensitivity_json),
                    "user_tier": user_tier,
                    "assigned_model": assigned_model,
                    "data_retention_flag": retention_flag,
                    "prev_hash": prev_hash
                }
                payload_bytes = json.dumps(payload_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
                self._last_hash = hashlib.sha256(payload_bytes).hexdigest()
            else:
                self._last_hash = "GENESIS"
            self._ready = True

    async def route(self, prompt: str, user_tier: str) -> RoutingDecision:
        """Routes prompt to appropriate model tier and logs dynamically to audit trail."""
        await self.ensure_table()

        # 1. Classify prompt sensitivity
        sensitivity = self.classifier.classify(prompt)

        # 2. Determine target model based on sensitivity & access privileges
        assigned_model = "Fable-5-Core"
        retention_required = False

        if sensitivity:
            if user_tier == "Trusted-Partner":
                assigned_model = "Mythos-5-Unleashed"
                retention_required = True  # Mandatory 30-day retention flag
            else:
                # Fallback policy for non-trusted tiers requesting restricted knowledge
                assigned_model = "Opus-4.8-Fallback"
                retention_required = False
        else:
            # Safe requests default to Fable-5 general public core
            assigned_model = "Fable-5-Core"
            retention_required = False

        # 3. Cryptographic logging and chaining
        timestamp = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        routing_id = hashlib.sha256(f"{timestamp}{prompt_hash}".encode()).hexdigest()

        sensitivity_json = json.dumps(sensitivity)
        retention_flag = 1 if retention_required else 0

        # Sign routing sequence (canonical JSON)
        payload_obj = {
            "timestamp": timestamp,
            "prompt_hash": prompt_hash,
            "detected_sensitivity": sensitivity,
            "user_tier": user_tier,
            "assigned_model": assigned_model,
            "data_retention_flag": retention_flag,
            "prev_hash": self._last_hash
        }
        payload_bytes = json.dumps(payload_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
        entry_hash = hashlib.sha256(payload_bytes).hexdigest()
        
        signature = self.ledger.private_key.sign(entry_hash.encode("utf-8")).hex()

        # Persist transaction
        await self._conn.execute(
            """INSERT INTO cognitive_router_log 
               (routing_id, timestamp, prompt_hash, detected_sensitivity, user_tier, 
                assigned_model, data_retention_flag, prev_hash, signature)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                routing_id,
                timestamp,
                prompt_hash,
                sensitivity_json,
                user_tier,
                assigned_model,
                retention_flag,
                self._last_hash,
                signature,
            ),
        )
        await self._conn.commit()


        # Update last hash chain pointer
        self._last_hash = entry_hash

        return RoutingDecision(
            routing_id=routing_id,
            timestamp=timestamp,
            assigned_model=assigned_model,
            sensitivity=sensitivity,
            retention_required=retention_required,
            signature=signature,
        )

    def verify_entry(self, entry: dict[str, Any], public_key: Any) -> bool:
        """Verifies a cognitive router log entry externally."""
        try:
            payload_obj = {
                "timestamp": entry["timestamp"],
                "prompt_hash": entry["prompt_hash"],
                "detected_sensitivity": entry["detected_sensitivity"],
                "user_tier": entry["user_tier"],
                "assigned_model": entry["assigned_model"],
                "data_retention_flag": entry["data_retention_flag"],
                "prev_hash": entry["prev_hash"]
            }
            payload_bytes = json.dumps(payload_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
            entry_hash = hashlib.sha256(payload_bytes).hexdigest()
            
            public_key.verify(
                bytes.fromhex(entry["signature"]),
                entry_hash.encode("utf-8")
            )
            return True
        except Exception:
            return False
