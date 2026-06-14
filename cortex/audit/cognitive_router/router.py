from __future__ import annotations

import logging

logger = logging.getLogger("cortex.audit.cognitive_router")

# [C5-REAL] Exergy-Maximized
"""
COGNITIVE-ROUTER: AI Cognitive Router Engine (Fable/Mythos State Machine).

Production-grade verifiable routing state machine featuring:
- Declarative policy DSL (YAML/JSON routing language).
- Deterministic classifier pipeline with hybrid keyword + semantic similarity matching.
- Replay debugger engine explaining matching rules and category triggers.
- Adversarial bypass simulator for stress testing classification.
"""


import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any

import yaml

from cortex.audit.ledger import EnterpriseAuditLedger

from .classifier import SafetyClassifier
from .models import _CREATE_ROUTER_LOG_SQL, RoutingDecision


class CognitiveRouter:
    """Dynamic cognitive routing engine between Fable 5, Mythos 5, and Fallback Opus 4.8."""

    DEFAULT_ROUTING_POLICY = {
        "version": "v2.0.0-declarative",
        "default_tier": "General-Public",
        "categories": SafetyClassifier.DEFAULT_CATEGORIES,
        "tiers": {
            "Trusted-Partner": {
                "rules": [
                    {
                        "match_category": "cybersecurity",
                        "assigned_model": "Mythos-5-Unleashed",
                        "retention_required": True,
                    },
                    {
                        "match_category": "biology",
                        "assigned_model": "Mythos-5-Unleashed",
                        "retention_required": True,
                    },
                    {
                        "match_category": "chemistry",
                        "assigned_model": "Mythos-5-Unleashed",
                        "retention_required": True,
                    },
                ],
                "default_model": "Fable-5-Core",
            },
            "General-Public": {
                "rules": [
                    {
                        "match_category": "cybersecurity",
                        "assigned_model": "Opus-4.8-Fallback",
                        "retention_required": False,
                    },
                    {
                        "match_category": "biology",
                        "assigned_model": "Opus-4.8-Fallback",
                        "retention_required": False,
                    },
                    {
                        "match_category": "chemistry",
                        "assigned_model": "Opus-4.8-Fallback",
                        "retention_required": False,
                    },
                ],
                "default_model": "Fable-5-Core",
            },
        },
    }

    def __init__(
        self,
        ledger: EnterpriseAuditLedger,
        routing_policy: dict[str, Any] | None = None,
        embedder: Any | None = None,
        semantic_threshold: float = 0.82,
    ) -> None:
        self.ledger = ledger
        self._conn = ledger._conn
        self.routing_policy = routing_policy or self.DEFAULT_ROUTING_POLICY

        # Load safety classifier with custom categories configured in policy DSL
        categories = self.routing_policy.get("categories", SafetyClassifier.DEFAULT_CATEGORIES)
        self.classifier = SafetyClassifier(
            categories_config=categories,
            embedder=embedder,
            semantic_threshold=semantic_threshold,
        )
        self._ready = False
        self._last_hash = "GENESIS"
        self._lock = asyncio.Lock()

    @classmethod
    def from_policy_yaml(
        cls, ledger: EnterpriseAuditLedger, yaml_str: str, **kwargs: Any
    ) -> CognitiveRouter:
        """Loads CognitiveRouter instance from a declarative YAML policy DSL."""
        policy = yaml.safe_load(yaml_str)
        return cls(ledger, routing_policy=policy, **kwargs)

    @classmethod
    def from_policy_json(
        cls, ledger: EnterpriseAuditLedger, json_str: str, **kwargs: Any
    ) -> CognitiveRouter:
        """Loads CognitiveRouter instance from a declarative JSON policy DSL."""
        policy = json.loads(json_str)
        return cls(ledger, routing_policy=policy, **kwargs)

    def canonical_json(self, payload_obj: dict[str, Any]) -> bytes:
        """Generates sorted, compact canonical bytes of log payload."""
        sensitivity = payload_obj.get("detected_sensitivity")
        if isinstance(sensitivity, str):
            try:
                sensitivity = json.loads(sensitivity)
            except Exception as e:
                logger.warning("Failed to load sensitivity from string: %s", e)
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
        """Ensures log table existence and migrates old schemas to support unique constraints."""
        if self._ready:
            return
        async with self._lock:
            if self._ready:
                return

            cursor = await self._conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='cognitive_router_log'"
            )
            row = await cursor.fetchone()
            if row:
                sql = row[0]
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

                        query = f"INSERT INTO cognitive_router_log ({', '.join(insert_cols)}) SELECT {', '.join(select_cols)} FROM _cognitive_router_log_old"  # noqa: S608
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
        """Classifies, matches declarative policy routing compiler rules, and signs transaction."""
        await self.ensure_table()

        sensitivity = await self.classifier.classify(prompt)

        # Map rules matching based on declarative config
        tier_policy = self.routing_policy["tiers"].get(user_tier)
        if not tier_policy:
            tier_policy = self.routing_policy["tiers"][self.routing_policy["default_tier"]]

        assigned_model = tier_policy.get("default_model") or tier_policy.get(
            "default", "Fable-5-Core"
        )
        retention_required = False

        if sensitivity:
            # Match first rule triggered by detected sensitivities
            matched = False
            for rule in tier_policy.get("rules", []):
                if rule["match_category"] in sensitivity:
                    assigned_model = rule["assigned_model"]
                    retention_required = rule.get("retention_required", False)
                    matched = True
                    break
            if not matched:
                # Default restricted fallback
                assigned_model = tier_policy.get("restricted_fallback_model") or tier_policy.get(
                    "restricted", "Opus-4.8-Fallback"
                )
                retention_required = tier_policy.get("retention_for_restricted", False)

        timestamp = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        routing_id = hashlib.sha256(f"{timestamp}{prompt_hash}".encode()).hexdigest()

        sensitivity_json = json.dumps(sensitivity)
        retention_flag = 1 if retention_required else 0

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
