# [C5-REAL] Exergy-Maximized
"""
COGNITIVE-ROUTER: AI Cognitive Router Engine (Fable/Mythos State Machine).

Production-grade verifiable routing state machine featuring:
- Declarative policy DSL (YAML/JSON routing language).
- Deterministic classifier pipeline with hybrid keyword + semantic similarity matching.
- Replay debugger engine explaining matching rules and category triggers.
- Adversarial bypass simulator for stress testing classification.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature

from babylon60.crypto.hash_registry import cortex_hash

try:
    import yaml
except ImportError:
    yaml = None

from babylon60.audit.cognitive_classifier import SafetyClassifier, cosine_similarity
from babylon60.audit.cognitive_config import DEFAULT_ROUTING_POLICY
from babylon60.audit.cognitive_debugger import RoutingReplayDebugger
from babylon60.audit.cognitive_simulator import AdversarialPromptSimulator
from babylon60.audit.ledger import EnterpriseAuditLedger

__all__ = [
    "CognitiveRouter",
    "RoutingDecision",
    "SafetyClassifier",
    "RoutingReplayDebugger",
    "AdversarialPromptSimulator",
    "cosine_similarity",
]

logger = logging.getLogger("cortex.audit.cognitive_router")


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


class CognitiveRouter:
    """Dynamic cognitive routing engine between Fable 5, Mythos 5, and Fallback Opus 4.8."""

    def __init__(
        self,
        ledger: EnterpriseAuditLedger,
        routing_policy: dict[str, Any] | None = None,
        embedder: Any | None = None,
        semantic_threshold: float = 0.82,
    ) -> None:
        self.ledger = ledger
        self._conn = ledger._conn
        self.routing_policy = routing_policy or DEFAULT_ROUTING_POLICY

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
        if yaml is None:
            raise ImportError("pyyaml is required to load YAML policies. Run pip install pyyaml.")
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
            except (ValueError, KeyError, RuntimeError) as e:
                logger.warning("Failed to parse sensitivity: %s", e)
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
        from babylon60.audit.cognitive_db import ensure_table_for_router

        await ensure_table_for_router(self)

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
        prompt_hash = cortex_hash(prompt.encode("utf-8"))
        routing_id = cortex_hash(f"{timestamp}{prompt_hash}".encode())

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
        entry_hash = cortex_hash(payload_bytes)

        signature = self.ledger.private_key.sign(entry_hash.encode("utf-8")).hex()

        from babylon60.database.core import causal_write

        with causal_write(self._conn):
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
            entry_hash = cortex_hash(payload_bytes)

            public_key.verify(bytes.fromhex(entry["signature"]), entry_hash.encode("utf-8"))
            return True
        except (ValueError, KeyError, RuntimeError, InvalidSignature) as e:
            logger.warning("Cognitive router verify failed: %s", e)
            return False
