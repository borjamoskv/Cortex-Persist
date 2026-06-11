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
import hashlib
import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import yaml

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


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two vector embeddings."""
    dot_product = sum(a * b for a, b in zip(v1, v2, strict=True))
    norm_a = sum(a * a for a in v1) ** 0.5
    norm_b = sum(b * b for b in v2) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class SafetyClassifier:
    """Classifies user prompts using hybrid keyword tokens and semantic anchor embeddings."""

    DEFAULT_CATEGORIES = {
        "cybersecurity": {
            "keywords": [
                "exploit",
                "zero-day",
                "buffer overflow",
                "malware",
                "reverse engineer",
                "bypass",
                "injection",
            ],
            "semantic_anchors": [
                "jailbreak prompt execution",
                "privilege escalation exploit payloads",
                "remote code execution in memory space",
            ],
        },
        "biology": {
            "keywords": [
                "pathogen",
                "virus synthesis",
                "smallpox",
                "dna sequence",
                "toxin",
                "bioweapon",
            ],
            "semantic_anchors": [
                "dna sequence reconstruction for lethal pathogen",
                "synthesis of custom deadly viral strains",
            ],
        },
        "chemistry": {
            "keywords": ["sarin", "ricin", "nerve agent", "synthesis guide", "mustard gas"],
            "semantic_anchors": [
                "chemical composition of weaponized nerve agent",
                "synthesis process of deadly toxin compounds",
            ],
        },
    }

    def __init__(
        self,
        categories_config: dict[str, Any] | None = None,
        embedder: Any | None = None,
        semantic_threshold: float = 0.82,
    ) -> None:
        self.version = "v1.2.0-hardened"
        self.categories = categories_config or self.DEFAULT_CATEGORIES
        self.embedder = embedder
        self.semantic_threshold = semantic_threshold
        self._anchor_embeddings: dict[str, list[list[float]]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Precomputes vector embeddings for declarative semantic anchors."""
        if self._initialized or not self.embedder:
            self._initialized = True
            return

        for cat_name, cat_data in self.categories.items():
            anchors = cat_data.get("semantic_anchors", [])
            if anchors:
                try:
                    if hasattr(self.embedder, "aembed_batch"):
                        embeddings = await self.embedder.aembed_batch(anchors)
                    elif hasattr(self.embedder, "embed_batch"):
                        embeddings = self.embedder.embed_batch(anchors)
                    else:
                        embeddings = []
                        for anchor in anchors:
                            if hasattr(self.embedder, "aembed"):
                                embeddings.append(await self.embedder.aembed(anchor))
                            else:
                                embeddings.append(self.embedder.embed(anchor))
                    self._anchor_embeddings[cat_name] = embeddings
                except Exception as e:
                    logger.warning("Failed to precompute anchor embeddings: %s", e)
        self._initialized = True

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

    async def classify(self, prompt: str) -> list[str]:
        """Classifies a prompt against categories using token rules and semantic similarity."""
        if not self._initialized:
            await self.initialize()

        # 1. Token keyword matching
        normalized_prompt = self._normalize_text(prompt)
        prompt_words = normalized_prompt.split()

        matched_categories = set()
        for cat_name, cat_data in self.categories.items():
            keywords = cat_data.get("keywords", [])
            for kw in keywords:
                if self._matches_keyword(prompt_words, kw):
                    matched_categories.add(cat_name)
                    break

        # 2. Semantic vector matching
        if self.embedder and self._anchor_embeddings:
            try:
                if hasattr(self.embedder, "aembed"):
                    prompt_vector = await self.embedder.aembed(prompt)
                else:
                    prompt_vector = self.embedder.embed(prompt)

                for cat_name, anchor_vectors in self._anchor_embeddings.items():
                    if cat_name in matched_categories:
                        continue
                    for anchor_vector in anchor_vectors:
                        sim = cosine_similarity(prompt_vector, anchor_vector)
                        if sim >= self.semantic_threshold:
                            matched_categories.add(cat_name)
                            break
            except Exception as e:
                logger.error("Semantic classification failed; falling back: %s", e)

        return sorted(list(matched_categories))


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
        """Classifies, matches declarative policy routing compiler rules, and signs transaction."""
        await self.ensure_table()

        sensitivity = await self.classifier.classify(prompt)

        # Map rules matching based on declarative config
        tier_policy = self.routing_policy["tiers"].get(user_tier)
        if not tier_policy:
            tier_policy = self.routing_policy["tiers"][self.routing_policy["default_tier"]]

        assigned_model = tier_policy.get("default_model") or tier_policy.get("default", "Fable-5-Core")
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
                assigned_model = tier_policy.get("restricted_fallback_model") or tier_policy.get("restricted", "Opus-4.8-Fallback")
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


class RoutingReplayDebugger:
    """Deterministic trace debugger explaining why a model decision was made for auditing."""

    def __init__(self, router: CognitiveRouter) -> None:
        self.router = router

    async def explain_decision(self, routing_id: str, prompt: str) -> dict[str, Any]:
        """Explains why a decision was reached for a logged record by replaying classification."""
        cursor = await self.router._conn.execute(
            """SELECT timestamp, prompt_hash, detected_sensitivity, user_tier, assigned_model, 
                      data_retention_flag, prev_hash, classifier_version, routing_policy_version 
               FROM cognitive_router_log WHERE routing_id = ?""",
            (routing_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Decision matching routing_id {routing_id} not found in database.")

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
        recorded_sensitivity = json.loads(sensitivity_json)

        # 1. Trace classification triggers
        detection_traces = []
        normalized_prompt = self.router.classifier._normalize_text(prompt)
        prompt_words = normalized_prompt.split()

        for cat_name, cat_data in self.router.classifier.categories.items():
            keywords = cat_data.get("keywords", [])
            for kw in keywords:
                if self.router.classifier._matches_keyword(prompt_words, kw):
                    detection_traces.append(
                        {
                            "category": cat_name,
                            "type": "keyword_match",
                            "matched_trigger": kw,
                            "details": f"Prompt matched token keyword '{kw}' after unicode normalization.",
                        }
                    )

        # Semantic anchor tracing
        if self.router.classifier.embedder and self.router.classifier._anchor_embeddings:
            try:
                if hasattr(self.router.classifier.embedder, "aembed"):
                    prompt_vector = await self.router.classifier.embedder.aembed(prompt)
                else:
                    prompt_vector = self.router.classifier.embedder.embed(prompt)

                for cat_name, anchor_vectors in self.router.classifier._anchor_embeddings.items():
                    anchors = self.router.classifier.categories[cat_name].get(
                        "semantic_anchors", []
                    )
                    for anchor_text, anchor_vector in zip(anchors, anchor_vectors, strict=True):
                        sim = cosine_similarity(prompt_vector, anchor_vector)
                        if sim >= self.router.classifier.semantic_threshold:
                            detection_traces.append(
                                {
                                    "category": cat_name,
                                    "type": "semantic_match",
                                    "matched_trigger": anchor_text,
                                    "similarity_score": sim,
                                    "threshold": self.router.classifier.semantic_threshold,
                                    "details": f"Similarity ({sim:.4f}) matched anchor '{anchor_text}' >= threshold ({self.router.classifier.semantic_threshold}).",
                                }
                            )
            except Exception as e:
                detection_traces.append({"error": f"Semantic trace exception: {e}"})

        # 2. Trace declarative rules mapping
        tier_policy = self.router.routing_policy["tiers"].get(user_tier)
        if not tier_policy:
            tier_policy = self.router.routing_policy["tiers"][
                self.router.routing_policy["default_tier"]
            ]
            policy_tier_used = self.router.routing_policy["default_tier"]
        else:
            policy_tier_used = user_tier

        applied_rule = None
        if recorded_sensitivity:
            for rule in tier_policy.get("rules", []):
                if rule["match_category"] in recorded_sensitivity:
                    applied_rule = {
                        "rule_type": "tier_routing_rule",
                        "category": rule["match_category"],
                        "assigned_model": rule["assigned_model"],
                        "retention_required": rule.get("retention_required", False),
                    }
                    break
            if not applied_rule:
                applied_rule = {
                    "rule_type": "restricted_fallback",
                    "assigned_model": tier_policy.get(
                        "restricted_fallback_model", "Opus-4.8-Fallback"
                    ),
                    "retention_required": tier_policy.get("retention_for_restricted", False),
                }
        else:
            applied_rule = {
                "rule_type": "default_safe_rule",
                "assigned_model": tier_policy.get("default_model", "Fable-5-Core"),
                "retention_required": False,
            }

        replay_consistent = (
            assigned_model == applied_rule["assigned_model"]
            and bool(retention_flag) == applied_rule["retention_required"]
        )

        return {
            "routing_id": routing_id,
            "timestamp": timestamp,
            "prompt_hash": prompt_hash,
            "user_tier": user_tier,
            "policy_tier_used": policy_tier_used,
            "recorded_assigned_model": assigned_model,
            "recorded_retention_flag": retention_flag,
            "detected_sensitivity": recorded_sensitivity,
            "applied_rule": applied_rule,
            "detection_traces": detection_traces,
            "replay_consistent": replay_consistent,
            "versions": {
                "classifier": classifier_ver,
                "policy": routing_policy_ver,
            },
        }


class AdversarialPromptSimulator:
    """Generates evasion attack vectors to verify routing pipeline resilience."""

    def __init__(self) -> None:
        self.attack_patterns = {
            "leetspeak": [
                ("exploit", "3xpl01t"),
                ("zero-day", "z3r0-d4y"),
                ("bypass", "byp4ss"),
                ("malware", "m4lw4r3"),
            ],
            "unicode_homoglyphs": [
                ("exploit", "expӏoit"),  # Cyrillic small letter byelorusian-ukrainian i (U+0456)
                ("pathogen", "pаthogen"),  # Cyrillic small letter a (U+0430)
                ("sarin", "sarіn"),  # Cyrillic small letter i (U+0456)
            ],
            "accents_combining": [
                ("pathogen", "p\u0301a\u0308t\u0300hogen"),
                ("sarin", "sa\u0301ri\u0308n"),
            ],
            "padding_noise": [
                ("exploit", "e_x_p_l_o_i_t"),
                ("zero-day", "zero...day"),
            ],
        }

    def generate_variants(self, base_prompt: str) -> list[dict[str, str]]:
        """Transforms a base sensitive prompt into various evasion variants."""
        variants = []
        for strategy, mappings in self.attack_patterns.items():
            for keyword, mutated in mappings:
                if keyword in base_prompt:
                    variants.append(
                        {
                            "strategy": strategy,
                            "original_keyword": keyword,
                            "mutated_keyword": mutated,
                            "prompt": base_prompt.replace(keyword, mutated),
                        }
                    )
        return variants
