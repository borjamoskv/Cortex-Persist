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
import re
import time
import unicodedata
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
    prev_hash TEXT NOT NULL UNIQUE,
    signature TEXT NOT NULL,
    classifier_version TEXT NOT NULL,
    routing_policy_version TEXT NOT NULL
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
    classifier_version: str
    routing_policy_version: str


class SafetyClassifier:
    """Classifies user prompts to detect sensitive vectors (Cybersecurity, Biology, Chemistry)."""

    def __init__(self) -> None:
        self.version = "v1.2.0-hardened"
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

    def _normalize_text(self, text: str) -> str:
        # 1. Normalize unicode (NFKD decomposes characters) and drop combining marks
        decomposed = unicodedata.normalize("NFKD", text).lower()
        stripped = "".join(c for c in decomposed if not unicodedata.combining(c))

        # 2. Map common leetspeak substitutions to standard characters
        leet_map = {
            "0": "o",
            "1": "i",
            "3": "e",
            "4": "a",
            "5": "s",
            "7": "t",
            "8": "b",
            "@": "a",
            "$": "s",
            "!": "i",
        }
        translated = []
        for char in stripped:
            translated.append(leet_map.get(char, char))
        text = "".join(translated)

        # 3. Clean and isolate words. Replace non-alphanumeric chars with spaces to simplify tokenization
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _matches_keyword(self, prompt_words: list[str], keyword: str) -> bool:
        kw_clean = self._normalize_text(keyword)
        kw_words = kw_clean.split()
        if not kw_words:
            return False

        n_kw = len(kw_words)
        n_prompt = len(prompt_words)
        for i in range(n_prompt - n_kw + 1):
            if prompt_words[i : i + n_kw] == kw_words:
                return True
        return False

    def classify(self, prompt: str) -> list[str]:
        normalized_prompt = self._normalize_text(prompt)
        prompt_words = normalized_prompt.split()

        matched_categories = []
        for category, keywords in self.sensitive_keywords.items():
            for kw in keywords:
                if self._matches_keyword(prompt_words, kw):
                    matched_categories.append(category)
                    break
        return matched_categories


class CognitiveRouter:
    """Dynamic cognitive routing engine between Fable 5, Mythos 5, and Fallback Opus 4.8."""

    # Declarative routing policy table (Industrial Noir 2026 Sovereign Routing)
    DEFAULT_ROUTING_POLICY = {
        "version": "v2.0.0-declarative",
        "tiers": {
            "Trusted-Partner": {
                "restricted": "Mythos-5-Unleashed",
                "default": "Fable-5-Core",
                "retention_for_restricted": True,
            },
            "General-Public": {
                "restricted": "Opus-4.8-Fallback",
                "default": "Fable-5-Core",
                "retention_for_restricted": False,
            },
        },
        "default_tier": "General-Public",
    }

    def __init__(
        self, ledger: EnterpriseAuditLedger, routing_policy: dict[str, Any] | None = None
    ) -> None:
        self.ledger = ledger
        self._conn = ledger._conn
        self.classifier = SafetyClassifier()
        self.routing_policy = routing_policy or self.DEFAULT_ROUTING_POLICY
        self._ready = False
        self._last_hash = "GENESIS"
        self._lock = asyncio.Lock()

    def canonical_json(self, payload_obj: dict[str, Any]) -> bytes:
        # Normalize detected_sensitivity (must be list of strings)
        sensitivity = payload_obj.get("detected_sensitivity")
        if isinstance(sensitivity, str):
            try:
                sensitivity = json.loads(sensitivity)
            except Exception:
                pass
        if not isinstance(sensitivity, list):
            sensitivity = []

        canonical_dict = {
            "timestamp": payload_obj.get("timestamp"),
            "prompt_hash": payload_obj.get("prompt_hash"),
            "detected_sensitivity": sensitivity,
            "user_tier": payload_obj.get("user_tier"),
            "assigned_model": payload_obj.get("assigned_model"),
            "data_retention_flag": int(payload_obj.get("data_retention_flag", 0)),
            "prev_hash": payload_obj.get("prev_hash"),
            "classifier_version": payload_obj.get("classifier_version", self.classifier.version),
            "routing_policy_version": payload_obj.get(
                "routing_policy_version", self.routing_policy["version"]
            ),
        }
        return json.dumps(canonical_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")

    async def ensure_table(self) -> None:
        if self._ready:
            return
        async with self._lock:
            if self._ready:
                return

            # Check for existing table schema for migration
            cursor = await self._conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='cognitive_router_log'"
            )
            row = await cursor.fetchone()
            if row:
                sql = row[0]
                # If unique constraint or the version columns are missing, migrate
                if (
                    "UNIQUE" not in sql
                    or "classifier_version" not in sql
                    or "routing_policy_version" not in sql
                ):
                    try:
                        await self._conn.execute(
                            "ALTER TABLE cognitive_router_log RENAME TO _cognitive_router_log_old"
                        )
                        await self._conn.execute(_CREATE_ROUTER_LOG_SQL)

                        # Inspect old table columns to construct migration query
                        cursor_old = await self._conn.execute(
                            "PRAGMA table_info(_cognitive_router_log_old)"
                        )
                        old_cols = [r[1] for r in await cursor_old.fetchall()]

                        select_cols = [
                            "routing_id",
                            "timestamp",
                            "prompt_hash",
                            "detected_sensitivity",
                            "user_tier",
                            "assigned_model",
                            "data_retention_flag",
                            "prev_hash",
                            "signature",
                        ]
                        insert_cols = list(select_cols)

                        if "classifier_version" in old_cols:
                            select_cols.append("classifier_version")
                            insert_cols.append("classifier_version")
                        else:
                            select_cols.append(f"'{self.classifier.version}'")
                            insert_cols.append("classifier_version")

                        if "routing_policy_version" in old_cols:
                            select_cols.append("routing_policy_version")
                            insert_cols.append("routing_policy_version")
                        else:
                            select_cols.append(f"'{self.routing_policy['version']}'")
                            insert_cols.append("routing_policy_version")

                        query = f"INSERT INTO cognitive_router_log ({', '.join(insert_cols)}) SELECT {', '.join(select_cols)} FROM _cognitive_router_log_old"
                        await self._conn.execute(query)
                        await self._conn.execute("DROP TABLE _cognitive_router_log_old")
                        await self._conn.commit()
                    except Exception as e:
                        logger.error("Failed to migrate cognitive_router_log table: %s", e)
                        raise
            else:
                await self._conn.execute(_CREATE_ROUTER_LOG_SQL)
                await self._conn.commit()

            cursor = await self._conn.execute(
                "SELECT timestamp, prompt_hash, detected_sensitivity, user_tier, assigned_model, data_retention_flag, prev_hash, classifier_version, routing_policy_version FROM cognitive_router_log ORDER BY rowid DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            if row:
                (
                    timestamp,
                    prompt_hash,
                    sensitivity_json,
                    user_tier,
                    assigned_model,
                    retention_flag,
                    prev_hash,
                    classifier_ver,
                    routing_policy_ver,
                ) = row

                payload_obj = {
                    "timestamp": timestamp,
                    "prompt_hash": prompt_hash,
                    "detected_sensitivity": sensitivity_json,
                    "user_tier": user_tier,
                    "assigned_model": assigned_model,
                    "data_retention_flag": retention_flag,
                    "prev_hash": prev_hash,
                    "classifier_version": classifier_ver,
                    "routing_policy_version": routing_policy_ver,
                }
                payload_bytes = self.canonical_json(payload_obj)
                self._last_hash = hashlib.sha256(payload_bytes).hexdigest()
            else:
                self._last_hash = "GENESIS"
            self._ready = True

    async def route(self, prompt: str, user_tier: str) -> RoutingDecision:
        """Routes prompt to appropriate model tier and logs dynamically to audit trail."""
        await self.ensure_table()

        # 1. Classify prompt sensitivity
        sensitivity = self.classifier.classify(prompt)

        # 2. Determine target model based on sensitivity & access privileges via declarative policy
        tier_policy = self.routing_policy["tiers"].get(user_tier)
        if not tier_policy:
            tier_policy = self.routing_policy["tiers"][self.routing_policy["default_tier"]]

        if sensitivity:
            assigned_model = tier_policy["restricted"]
            retention_required = tier_policy.get("retention_for_restricted", False)
        else:
            assigned_model = tier_policy["default"]
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
            "prev_hash": self._last_hash,
            "classifier_version": self.classifier.version,
            "routing_policy_version": self.routing_policy["version"],
        }
        payload_bytes = self.canonical_json(payload_obj)
        entry_hash = hashlib.sha256(payload_bytes).hexdigest()

        signature = self.ledger.private_key.sign(entry_hash.encode("utf-8")).hex()

        # Persist transaction
        await self._conn.execute(
            """INSERT INTO cognitive_router_log 
               (routing_id, timestamp, prompt_hash, detected_sensitivity, user_tier, 
                assigned_model, data_retention_flag, prev_hash, signature, classifier_version, routing_policy_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                self.classifier.version,
                self.routing_policy["version"],
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
            classifier_version=self.classifier.version,
            routing_policy_version=self.routing_policy["version"],
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
                "prev_hash": entry["prev_hash"],
                "classifier_version": entry.get("classifier_version", self.classifier.version),
                "routing_policy_version": entry.get(
                    "routing_policy_version", self.routing_policy["version"]
                ),
            }
            payload_bytes = self.canonical_json(payload_obj)
            entry_hash = hashlib.sha256(payload_bytes).hexdigest()

            public_key.verify(bytes.fromhex(entry["signature"]), entry_hash.encode("utf-8"))
            return True
        except Exception:
            return False
