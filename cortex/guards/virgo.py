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

from cortex.crypto.keys import ZKSwarmIdentity
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

    def __init__(self, engine: Any = None, trust_penalty: float = 5.0) -> None:
        self.engine = engine
        self.trust_penalty = trust_penalty

    async def _check_agent_validation_signature(
        self,
        content: str,
        project: str,
        meta: dict[str, Any],
        agent_id: str | None,
        conn: aiosqlite.Connection,
        tenant_id: str = "cortex_default",
    ) -> None:
        """Verify the cryptographic Logos-Critique validation signature for an agent's fact."""
        logos_signature = meta.get("logos_signature")
        agent_public_key = meta.get("agent_public_key")
        nonce = meta.get("nonce", "")

        import os

        virgo_mode = os.environ.get("CORTEX_VIRGO_MODE", "STRICT").upper()
        if virgo_mode not in ("STRICT", "LEGACY", "TEST"):
            virgo_mode = "STRICT"

        if not logos_signature:
            if virgo_mode == "TEST":
                # Bypass missing signature error for non-Virgo tests in relaxed test environments
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

        # B. Fallback to Deterministic HMAC/Hash binding (LEGACY or TEST mode)
        if not is_valid_sig and virgo_mode in ("LEGACY", "TEST"):
            # Expected deterministic hash: sha256(content + str(nonce) + project)
            expected_hash = hashlib.sha256(f"{content}{nonce}{project}".encode()).hexdigest()
            if logos_signature == expected_hash:
                is_valid_sig = True

        # C. Verify agent registered key matches (if registered and signature is valid)
        if is_valid_sig and agent_id and agent_public_key:
            from cortex.crypto.keys import KeyManager
            try:
                km = KeyManager(tenant_id=tenant_id)
                registered_key = km._metadata.get(agent_id, {}).get("public_key_b64")
                if registered_key and registered_key != agent_public_key:
                    is_valid_sig = False
                    logger.error(f"Agent key mismatch: key passed {agent_public_key[:16]}... does not match registered key {registered_key[:16]}...")
            except Exception as e:
                logger.debug(f"Could not load KeyManager metadata for agent key verification: {e}")



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

        # 0. Tenant Context Validation
        meta_tenant = meta.get("tenant_id")
        if meta_tenant and meta_tenant != tenant_id:
            self._apply_trust_penalty(agent_id, taint_severity=0.5)
            await self._trigger_ledger_rollback(
                conn, f"Tenant mismatch: metadata tenant '{meta_tenant}' does not match context tenant '{tenant_id}'."
            )

        # Determine if this write originates from an autonomous agent
        is_agent = (
            source.startswith("agent:")
            or agent_id is not None
            or fact_type in ("decision", "rule", "code")
        )

        if not is_agent:
            # Low-risk system/user inputs can bypass strict agent signatures
            return

        # 1. Context Poisoning Scans (Epistemic Drift & Recursive loops)
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

        # 2. Deterministic Validation Signature Verification
        await self._check_agent_validation_signature(content, project, meta, agent_id, conn, tenant_id)

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
        except (ValueError, TypeError, KeyError, AssertionError) as e:
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
        except (ValueError, TypeError, KeyError, AssertionError) as e:
            logger.warning("⚠️ [VIRGO-ROLLBACK] Rollback call completed with exception: %s", e)

        raise error_class(f"Logos-Critique (Virgo ♍) Rejected: {reason}")
