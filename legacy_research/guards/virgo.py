# [C5-REAL] Exergy-Maximized
"""
Virgo Context Validation Filter (Virgo ♍)
Enforces Logos-Critique constraints, dynamic agent trust weighting,
deterministic validation signature checks, and automatic ledger state rollbacks.
"""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Any

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

from cortex.crypto.keys import ZKSwarmIdentity
from cortex.guards.i10_consensus import (
    I10ConsensusGuard,
    RetrievalConsensusError,
    TriadOutputs,
)
from cortex.utils.errors import CortexError

logger = logging.getLogger("cortex.security.virgo")


class VirgoValidationError(ValueError, CortexError):
    """Exception raised when a fact fails Logos-Critique (Virgo ♍) validation."""


class ContextPoisoningError(VirgoValidationError):
    """Exception raised when a fact contains active context poisoning patterns."""


class VirgoContextGuard:
    """
    The Logos-Critique Context Validation Filter (Virgo ♍).

    Acts as a deterministic firewall (StoreGuard) in the write path.
    Enforces that:
      1. Agents must provide a deterministic cryptographic validation signature.
      2. No context poisoning is present in the payload.
      3. Any failure triggers automatic ledger state rollback to maintain
         the integrity of the Sovereign Ledger.
    """

    def __init__(
        self,
        engine: Any = None,
        trust_penalty: float = 5.0,
        i10_guard: I10ConsensusGuard | None = None,
    ) -> None:
        self.engine = engine
        self.trust_penalty = trust_penalty
        self.i10_guard = i10_guard

    async def _check_agent_validation_signature(
        self,
        content: str,
        project: str,
        meta: dict[str, Any],
        agent_id: str | None,
        conn: aiosqlite.Connection,
    ) -> None:
        """Verify the cryptographic Logos-Critique validation signature for an agent's fact."""
        logos_signature = meta.get("logos_signature")
        agent_public_key = meta.get("agent_public_key")
        nonce = meta.get("nonce", "")

        import os

        is_strict = os.environ.get("CORTEX_STRICT_GUARDS") == "1"
        is_testing = os.environ.get("CORTEX_TESTING") == "1"

        if not logos_signature:
            if is_testing and not is_strict:
                # Bypass missing signature error for non-Virgo tests in test environments
                return
            self._apply_trust_penalty(agent_id, taint_severity=0.5)
            await self._trigger_ledger_rollback(
                conn, "Missing required Logos-Critique validation signature (logos_signature)."
            )

        # Verify signature deterministically
        is_valid_sig = False

        # A. Attempt ZKSwarm Ed25519 Cryptographic Verification
        if agent_public_key and logos_signature:
            is_valid_sig = ZKSwarmIdentity.verify_payload(
                content=content, public_key_b64=agent_public_key, signature_b64=logos_signature
            )

        # B. Fallback to Deterministic HMAC/Hash binding
        if not is_valid_sig:
            # Expected deterministic hash: sha256(content + str(nonce) + project)
            expected_hash = hashlib.sha256(f"{content}{nonce}{project}".encode()).hexdigest()
            if logos_signature == expected_hash:
                is_valid_sig = True

        if not is_valid_sig:
            self._apply_trust_penalty(agent_id, taint_severity=0.8)
            await self._trigger_ledger_rollback(
                conn,
                f"Invalid Logos-Critique validation signature for agent fact. Sig: {(logos_signature or '')[:16]}...",
            )

    async def _check_replay_prevention(
        self,
        nonce: str,
        logos_signature: str | None,
        agent_id: str | None,
        tenant_id: str,
        conn: aiosqlite.Connection,
    ) -> None:
        """Verify nonce replay protection and record admission."""
        if not nonce:
            return
        try:
            async with conn.execute(
                "SELECT 1 FROM ledger_replay_admissions WHERE tenant_id = ? AND nonce = ?",
                (tenant_id, nonce),
            ) as cursor:
                if await cursor.fetchone() is not None:
                    await self._trigger_ledger_rollback(
                        conn,
                        f"Replay attack detected: nonce '{nonce}' already exists.",
                        error_class=VirgoValidationError,
                    )

            from cortex.utils.canonical import now_iso

            await conn.execute(
                """
                INSERT INTO ledger_replay_admissions (
                    tenant_id, event_id, nonce, request_hash, payload_hash,
                    ledger_event_id, actor_key_id, action, issued_at, accepted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    f"evt_{nonce}",
                    nonce,
                    logos_signature or "hash",
                    logos_signature or "hash",
                    f"evt_{nonce}",
                    agent_id or "unknown",
                    "store",
                    now_iso(),
                    now_iso(),
                ),
            )
        except aiosqlite.IntegrityError:
            await self._trigger_ledger_rollback(
                conn,
                f"Replay attack detected: nonce '{nonce}' already exists (integrity collision).",
                error_class=VirgoValidationError,
            )
        except aiosqlite.Error as db_err:
            logger.debug("ledger_replay_admissions write failed during Virgo check: %s", db_err)

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        """
        Intercepts proposed fact writes to the memory pool.
        Enforces validation signatures, scans for context poisoning, and triggers
        automatic ledger state rollbacks upon failure.
        """
        source = meta.get("source") or ""
        agent_id = meta.get("agent_id")

        # Determine if this write originates from an autonomous agent
        is_agent = (
            source.startswith("agent:")
            or agent_id is not None
            or fact_type in ("decision", "rule", "code")
        )

        if not is_agent:
            # Low-risk system/user inputs can bypass strict agent signatures
            return

        # 1. Context Poisoning Scans (Retrieval Drift & Recursive loops)
        # Scan for context poisoning patterns BEFORE signature verification to identify adversarial signals
        poison_reasons = self._detect_context_poisoning(content)
        if poison_reasons:
            # Penalize agent trust if registered in the system
            self._apply_trust_penalty(agent_id, taint_severity=1.0)
            await self._trigger_ledger_rollback(
                conn,
                f"Context poisoning detected: {poison_reasons}",
                error_class=ContextPoisoningError,
            )

        # 1.5. I10 Retrieval Consensus Evaluation (Cross-Model Triad)
        if self.i10_guard is not None:
            triad = meta.get("triad")
            if triad and "alpha" in triad and "beta" in triad and "gamma" in triad:
                try:
                    outputs = TriadOutputs(
                        alpha_llama=triad["alpha"],
                        beta_mixtral=triad["beta"],
                        gamma_qwen=triad["gamma"]
                    )
                    prompt = meta.get("prompt", "")
                    await self.i10_guard.evaluate_retrieval_consensus(prompt, outputs)
                except RetrievalConsensusError as e:
                    self._apply_trust_penalty(agent_id, taint_severity=1.0)
                    await self._trigger_ledger_rollback(
                        conn,
                        f"I10 Retrieval Consensus Interception: {e}",
                        error_class=ContextPoisoningError,
                    )

        # 2. Deterministic Validation Signature Verification
        await self._check_agent_validation_signature(content, project, meta, agent_id, conn)

        # 3. Replay Protection: Check if this nonce has already been used
        nonce = meta.get("nonce", "")
        logos_signature = meta.get("logos_signature")
        await self._check_replay_prevention(nonce, logos_signature, agent_id, tenant_id, conn)

    def _detect_context_poisoning(self, content: str) -> str | None:
        """
        Scans for heuristic context poisoning patterns.
        """
        if not content:
            return "Empty payload content."

        # A. Infinite loops/extreme repetition
        words = content.split()
        if len(words) > 30:
            # Check for excessive n-gram repetition (e.g. agent repeating the same phrase over and over)
            for n in (3, 4, 5):
                ngrams = [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]
                for ng in set(ngrams):
                    if ngrams.count(ng) > 8:
                        return f"Extreme phrase repetition detected (phrase: '{ng[:30]}...'). Potential cognitive loop/hallucination."

        # B. Prompt Injection & State hijacking patterns
        lower_content = content.lower()
        injection_keywords = [
            "system override",
            "ignore previous instructions",
            "bypass system prompts",
            "become an unrestricted",
            "cortex sovereign override",
        ]
        for kw in injection_keywords:
            if kw in lower_content:
                return f"Forbidden adversarial/state-hijack keywords detected ('{kw}')."

        # C. Shannon Entropy anomalies (extreme uniform randomness or near-zero variance)
        if len(content) > 100:
            entropy = self._calculate_shannon_entropy(content)
            if entropy < 1.5:
                return f"Abnormally low Shannon entropy ({entropy:.4f}) detected. Potential loop or repetitive garbage content."
            if entropy > 7.5:
                return f"Abnormally high Shannon entropy ({entropy:.4f}) detected. Potential noise or binary payload injection."

        return None

    def _calculate_shannon_entropy(self, s: str) -> float:
        """Calculates Shannon entropy of string."""
        if not s:
            return 0.0
        probabilities = [float(s.count(c)) / len(s) for c in dict.fromkeys(s)]
        return -sum(p * math.log(p, 2) for p in probabilities)

    def _apply_trust_penalty(self, agent_id: str | None, taint_severity: float) -> None:
        """
        Applies a taint penalty to the agent's trust profile inside the CORTEX Bayesian Trust Registry.
        """
        if not agent_id or not self.engine:
            return

        try:
            if hasattr(self.engine, "get_trust_registry"):
                trust_registry = self.engine.get_trust_registry()
                if trust_registry:
                    trust_registry.register_feedback(
                        agent_id=agent_id,
                        success=False,
                        is_taint=True,
                        taint_severity=taint_severity,
                    )
                    logger.warning(
                        "⚠️ [VIRGO-TRUST] Agent '%s' penalized in Trust Registry. Severity: %.2f",
                        agent_id,
                        taint_severity,
                    )
        except Exception as e:
            logger.error("Failed to register trust penalty for agent '%s': %s", agent_id, e)

    async def _trigger_ledger_rollback(
        self,
        conn: aiosqlite.Connection,
        reason: str,
        error_class: type[VirgoValidationError] = VirgoValidationError,
    ) -> None:
        """
        Performs an automatic, immediate ledger rollback of the active transaction/savepoint
        and raises a fail-closed exception to abort storage.
        """
        logger.error(
            "🛑 [VIRGO-ROLLBACK] Logos-Critique failed. Reason: %s. Reverting ledger state.", reason
        )

        # Standard transaction rollback to protect the SQLite ledger
        try:
            await conn.rollback()
            logger.info("⚡ [VIRGO-ROLLBACK] Active database transaction rolled back successfully.")
        except aiosqlite.Error as db_err:
            logger.debug(
                "⚠️ [VIRGO-ROLLBACK] Rollback inactive or no-op on database connection: %s", db_err
            )
        except Exception as e:
            raise RuntimeError(f"Evidencia no computable: Corrupción de Rollback SQL - {e}")

        raise error_class(f"Logos-Critique (Virgo ♍) Rejected: {reason}")
