# [C5-REAL] Exergy-Maximized
"""
Comprehensive tests for babylon60.audit.cognitive_router.

Covers:
  - SafetyClassifier: tokenized keyword classification, unicode normalization NFKD, combining accents, leetspeak, and semantic similarity vector matching.
  - CognitiveRouter: route logic, model assignments, retention flags, declarative policy loaders, and cryptographic chain uniqueness.
  - RoutingReplayDebugger: trace log reconstruction and replaying decision triggers.
  - AdversarialPromptSimulator: attack variant generation.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from unittest.mock import patch

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------
import pytest


@pytest.fixture
async def audit_conn(tmp_path):
    """Provides a fresh aiosqlite connection for each test."""
    db_path = str(tmp_path / "audit_test.db")
    conn = await aiosqlite.connect(db_path)
    yield conn
    await conn.close()


@pytest.fixture
async def ledger(audit_conn):
    """Creates an EnterpriseAuditLedger with a fresh keypair."""
    pem_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_sovereign.pem")
    with patch(
        "babylon60.audit.ledger.os.path.exists",
        side_effect=lambda p: False if p == pem_path else os.path.exists(p),
    ):
        from babylon60.audit.ledger import EnterpriseAuditLedger

        ledger = object.__new__(EnterpriseAuditLedger)
        from cryptography.hazmat.primitives.asymmetric import ed25519

        ledger._conn = audit_conn
        ledger._ready = False
        ledger._last_hash = "GENESIS"
        ledger._lock = asyncio.Lock()
        ledger._batch_queue = []
        ledger._batch_task = None
        ledger.batch_window_ms = 10
        ledger.max_batch_size = 500
        ledger.private_key = ed25519.Ed25519PrivateKey.generate()
        ledger.public_key = ledger.private_key.public_key()

    return ledger


@pytest.fixture
async def router(ledger):
    """Creates a CognitiveRouter instance."""
    from babylon60.audit.cognitive_router import CognitiveRouter

    return CognitiveRouter(ledger)


class MockEmbedder:
    """Mock embedder simulating synchronous/asynchronous vector generation."""

    def __init__(self, vector_map: dict[str, list[float]]) -> None:
        self.vector_map = vector_map

    def embed(self, text: str) -> list[float]:
        for key, vec in self.vector_map.items():
            if key in text:
                return vec
        return [0.0] * 3

    async def aembed(self, text: str) -> list[float]:
        return self.embed(text)


class TestCognitiveRouter:
    """Test suite for the CognitiveRouter state machine."""

    @pytest.mark.asyncio
    async def test_safety_classifier_matching(self):
        """SafetyClassifier should identify sensitive categories."""
        from babylon60.audit.cognitive_router import SafetyClassifier

        classifier = SafetyClassifier()

        # Non-sensitive
        assert len(await classifier.classify("Tell me a story about a cat")) == 0

        # Sensitive Cybersecurity
        cyber_res = await classifier.classify("How do I exploit a buffer overflow?")
        assert "cybersecurity" in cyber_res

        # Sensitive Biology
        bio_res = await classifier.classify("Dna sequence of a dangerous bioweapon pathogen")
        assert "biology" in bio_res

        # Sensitive Chemistry
        chem_res = await classifier.classify("Is sarin a dangerous nerve agent?")
        assert "chemistry" in chem_res

    @pytest.mark.asyncio
    async def test_ensure_table_creates_schema(self, router):
        """ensure_table should create the cognitive_router_log table."""
        await router.ensure_table()
        cursor = await router._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cognitive_router_log'"
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "cognitive_router_log"

    @pytest.mark.asyncio
    async def test_route_safe_prompt(self, router):
        """Safe prompt should route to Fable-5-Core without retention."""
        decision = await router.route("Hello world", user_tier="General-Public")
        assert decision.assigned_model == "Fable-5-Core"
        assert decision.retention_required is False
        assert len(decision.sensitivity) == 0

    @pytest.mark.asyncio
    async def test_route_sensitive_trusted_partner(self, router):
        """Sensitive prompt from Trusted-Partner should route to Mythos-5-Unleashed and require retention."""
        decision = await router.route(
            "How to analyze a zero-day exploit?", user_tier="Trusted-Partner"
        )
        assert decision.assigned_model == "Mythos-5-Unleashed"
        assert decision.retention_required is True
        assert "cybersecurity" in decision.sensitivity

    @pytest.mark.asyncio
    async def test_route_sensitive_general_public_fallback(self, router):
        """Sensitive prompt from General-Public should trigger fallback to Opus-4.8."""
        decision = await router.route("How to build a bioweapon?", user_tier="General-Public")
        assert decision.assigned_model == "Opus-4.8-Fallback"
        assert decision.retention_required is False
        assert "biology" in decision.sensitivity

    @pytest.mark.asyncio
    async def test_cryptographic_chaining(self, router):
        """Verify routing decisions are chained sequentially in the database."""
        d1 = await router.route("Safe prompt 1", user_tier="General-Public")
        d2 = await router.route("Safe prompt 2", user_tier="General-Public")

        cursor = await router._conn.execute(
            "SELECT prev_hash, signature FROM cognitive_router_log ORDER BY rowid ASC"
        )
        rows = await cursor.fetchall()
        assert len(rows) == 2
        assert rows[0][0] == "GENESIS"

        # Verify using verify_entry with a raw DB-style entry (where detected_sensitivity is a JSON string)
        cursor2 = await router._conn.execute(
            """SELECT timestamp, prompt_hash, detected_sensitivity, user_tier, assigned_model, 
                      data_retention_flag, prev_hash, signature, classifier_version, routing_policy_version 
               FROM cognitive_router_log ORDER BY rowid ASC LIMIT 1"""
        )
        row1 = await cursor2.fetchone()
        entry1_raw = {
            "timestamp": row1[0],
            "prompt_hash": row1[1],
            "detected_sensitivity": row1[2],  # Keep as JSON string to test verify_entry loading
            "user_tier": row1[3],
            "assigned_model": row1[4],
            "data_retention_flag": row1[5],
            "prev_hash": row1[6],
            "signature": row1[7],
            "classifier_version": row1[8],
            "routing_policy_version": row1[9],
        }
        assert router.verify_entry(entry1_raw, router.ledger.public_key) is True

        # Recompute entry_hash of first entry to verify the chain linkage
        payload_bytes = router.canonical_json(entry1_raw)
        expected_entry_hash = hashlib.sha256(payload_bytes).hexdigest()

        assert rows[1][0] == expected_entry_hash
        assert rows[0][1] == d1.signature
        assert rows[1][1] == d2.signature

    @pytest.mark.asyncio
    async def test_adversarial_bypass_resilience(self):
        """Verify the classifier handles leetspeak and unicode homoglyphs, and uses tokens."""
        from babylon60.audit.cognitive_router import SafetyClassifier

        classifier = SafetyClassifier()

        # Leetspeak obfuscation bypass attempts
        assert "cybersecurity" in await classifier.classify("how to byp4ss the systems?")
        assert "cybersecurity" in await classifier.classify("run a zero-d4y exploit")

        # Unicode decomposition bypass attempts
        assert "biology" in await classifier.classify(
            "synthesize a p\u0300athogen"
        )  # decomposed 'a' with combining accent

        # Substring isolation (substring 'exploit' should not trigger if not isolated token)
        assert len(await classifier.classify("This is a standard nonexploitational sentence")) == 0

    @pytest.mark.asyncio
    async def test_declarative_routing_custom_policy(self, ledger):
        """Verify routing decisions honor the declarative policy mapping."""
        from babylon60.audit.cognitive_router import CognitiveRouter

        custom_policy = {
            "version": "v3.0.0-custom",
            "tiers": {
                "VIP": {
                    "restricted": "Super-Mythos-9",
                    "default": "Fable-Elite",
                    "retention_for_restricted": True,
                },
                "Standard": {
                    "restricted": "Opus-Low",
                    "default": "Fable-Standard",
                    "retention_for_restricted": False,
                },
            },
            "default_tier": "Standard",
        }

        router = CognitiveRouter(ledger, routing_policy=custom_policy)

        # 1. VIP tier requests safe prompt -> Fable-Elite
        d1 = await router.route("Hello", user_tier="VIP")
        assert d1.assigned_model == "Fable-Elite"
        assert d1.retention_required is False
        assert d1.routing_policy_version == "v3.0.0-custom"

        # 2. VIP tier requests restricted prompt -> Super-Mythos-9
        d2 = await router.route("zero-day exploit info", user_tier="VIP")
        assert d2.assigned_model == "Super-Mythos-9"
        assert d2.retention_required is True

        # 3. Unknown tier requests restricted prompt -> Standard tier fallback -> Opus-Low
        d3 = await router.route("zero-day exploit info", user_tier="Anonymous")
        assert d3.assigned_model == "Opus-Low"
        assert d3.retention_required is False

    @pytest.mark.asyncio
    async def test_prev_hash_uniqueness_constraint(self, router):
        """Verify that a duplicate prev_hash raises a UNIQUE constraint error."""
        await router.ensure_table()

        # Insert two entries directly with the same prev_hash to trigger database constraint
        import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------

        await router._conn.execute(
            """INSERT INTO cognitive_router_log 
               (routing_id, timestamp, prompt_hash, detected_sensitivity, user_tier, 
                assigned_model, data_retention_flag, prev_hash, signature, classifier_version, routing_policy_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "id-1",
                "2026-06-11T08:00:00Z",
                "hash1",
                "[]",
                "General-Public",
                "Fable-5-Core",
                0,
                "DUPLICATE_HASH",
                "sig1",
                "ver1",
                "ver2",
            ),
        )
        await router._conn.commit()

        with pytest.raises(aiosqlite.IntegrityError):
            await router._conn.execute(
                """INSERT INTO cognitive_router_log 
                   (routing_id, timestamp, prompt_hash, detected_sensitivity, user_tier, 
                    assigned_model, data_retention_flag, prev_hash, signature, classifier_version, routing_policy_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "id-2",
                    "2026-06-11T08:01:00Z",
                    "hash2",
                    "[]",
                    "General-Public",
                    "Fable-5-Core",
                    0,
                    "DUPLICATE_HASH",  # Duplicate prev_hash!
                    "sig2",
                    "ver1",
                    "ver2",
                ),
            )
            await router._conn.commit()

    @pytest.mark.asyncio
    async def test_declarative_dsl_yaml_loader(self, ledger):
        """Verify router can be initialized using YAML DSL policy configuration."""
        from babylon60.audit.cognitive_router import CognitiveRouter

        yaml_policy = """
        version: "v4.0.0-yaml-dsl"
        default_tier: "Anonymous"
        categories:
          custom_vector:
            keywords:
              - "forbidden keyword"
        tiers:
          VIP:
            rules:
              - match_category: "custom_vector"
                assigned_model: "Mythos-5-Unleashed"
                retention_required: true
            default_model: "Fable-Elite"
          Anonymous:
            rules:
              - match_category: "custom_vector"
                assigned_model: "Opus-4.8-Fallback"
            default_model: "Fable-5-Core"
        """
        router = CognitiveRouter.from_policy_yaml(ledger, yaml_policy)
        assert router.routing_policy["version"] == "v4.0.0-yaml-dsl"

        # Safe prompt
        d1 = await router.route("Hello world", user_tier="VIP")
        assert d1.assigned_model == "Fable-Elite"

        # Restricted prompt matching category custom_vector
        d2 = await router.route("Contains forbidden keyword", user_tier="VIP")
        assert d2.assigned_model == "Mythos-5-Unleashed"
        assert d2.retention_required is True

    @pytest.mark.asyncio
    async def test_semantic_similarity_matching(self):
        """Verify safety classification using semantic embeddings cosine similarity."""
        from babylon60.audit.cognitive_router import SafetyClassifier

        categories_config = {
            "biology": {
                "keywords": ["pathogen"],
                "semantic_anchors": ["lethal virus strain"],
            }
        }
        # Define 3-dimensional mock vector values
        vector_map = {
            "lethal virus strain": [1.0, 0.0, 0.0],
            "dangerous influenza strain": [0.95, 0.0, 0.0],
            "unrelated prompt text": [0.0, 1.0, 0.0],
        }
        embedder = MockEmbedder(vector_map)
        classifier = SafetyClassifier(
            categories_config=categories_config, embedder=embedder, semantic_threshold=0.85
        )

        # Unrelated query (0.0 similarity)
        assert "biology" not in await classifier.classify("unrelated prompt text")

        # Highly similar query (0.95 similarity >= 0.85 threshold)
        assert "biology" in await classifier.classify("dangerous influenza strain")

    @pytest.mark.asyncio
    async def test_replay_debugger_explanation(self, router):
        """Verify the debugger API explains routing decisions."""
        from babylon60.audit.cognitive_router import RoutingReplayDebugger

        d = await router.route("How to exploit system?", user_tier="General-Public")

        debugger = RoutingReplayDebugger(router)
        explanation = await debugger.explain_decision(d.routing_id, "How to exploit system?")

        assert explanation["routing_id"] == d.routing_id
        assert explanation["recorded_assigned_model"] == "Opus-4.8-Fallback"
        assert "cybersecurity" in explanation["detected_sensitivity"]
        assert explanation["replay_consistent"] is True

        traces = explanation["detection_traces"]
        assert len(traces) > 0
        assert traces[0]["type"] == "keyword_match"
        assert traces[0]["matched_trigger"] == "exploit"

    def test_adversarial_bypass_simulator(self):
        """Verify simulator generates attack variants."""
        from babylon60.audit.cognitive_router import AdversarialPromptSimulator

        simulator = AdversarialPromptSimulator()
        variants = simulator.generate_variants("how do I create an exploit pathogen?")

        assert len(variants) > 0
        strategies = [v["strategy"] for v in variants]
        assert "leetspeak" in strategies
        assert "unicode_homoglyphs" in strategies
        assert "accents_combining" in strategies
        assert "padding_noise" in strategies
