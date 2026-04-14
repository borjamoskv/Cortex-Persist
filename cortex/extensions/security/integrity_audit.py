"""
CORTEX v8 — Integrity Auditor.

Daily cryptographic integrity audit for the fact ledger.
Verifies Ed25519 signatures, SHA-256 hash chain continuity,
and detects orphaned/tampered facts.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from cortex import config
from cortex.database.core import connect_async_ctx

logger = logging.getLogger("cortex.extensions.security.integrity_audit")

__all__ = [
    "IntegrityAuditor",
    "AuditReport",
    "ChainStatus",
    "TamperedFact",
]

# ── Rust acceleration (optional) ─────────────────────────────────────────────
# Batch Ed25519 verification is CPU-bound and blocks the async event loop when
# done purely in Python.  The `cortex_rs` native extension releases the GIL for
# the entire batch, dramatically increasing throughput at scale.
try:
    import cortex_rs as _cortex_rs

    _RUST_AVAILABLE = True
    logger.debug("cortex_rs Rust extension loaded — batch Ed25519 via Rust")
except ImportError:
    _cortex_rs = None  # type: ignore[assignment]
    _RUST_AVAILABLE = False
    logger.debug("cortex_rs not available — falling back to per-fact Python verification")


# ═══════════════════════════════════════
# Data Models
# ═══════════════════════════════════════


@dataclass(frozen=True)
class TamperedFact:
    """A fact with invalid integrity."""

    fact_id: int
    issue: str  # "signature_invalid", "hash_mismatch", "orphaned_chain"
    expected: str = ""
    actual: str = ""
    content_preview: str = ""


@dataclass()
class ChainStatus:
    """Status of the hash chain."""

    is_valid: bool = True
    total_facts: int = 0
    verified: int = 0
    broken_links: list[TamperedFact] = field(default_factory=list)
    orphaned_facts: list[TamperedFact] = field(default_factory=list)


@dataclass()
class AuditReport:
    """Full integrity audit report."""

    timestamp: str = ""
    chain_status: ChainStatus = field(default_factory=ChainStatus)
    signature_failures: list[TamperedFact] = field(default_factory=list)
    total_facts: int = 0
    facts_with_signatures: int = 0
    facts_verified: int = 0
    duration_seconds: float = 0.0
    is_clean: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "is_clean": self.is_clean,
            "total_facts": self.total_facts,
            "facts_with_signatures": self.facts_with_signatures,
            "facts_verified": self.facts_verified,
            "chain_valid": self.chain_status.is_valid,
            "broken_links": len(self.chain_status.broken_links),
            "orphaned_facts": len(self.chain_status.orphaned_facts),
            "signature_failures": len(self.signature_failures),
            "duration_seconds": round(self.duration_seconds, 2),
        }


# ═══════════════════════════════════════
# Integrity Auditor
# ═══════════════════════════════════════


class IntegrityAuditor:
    """Daily cryptographic integrity audit for CORTEX facts.

    Verifies:
    1. SHA-256 hash chain continuity (prev_hash → current)
    2. Ed25519 digital signatures on signed facts
    3. Orphaned facts (broken chain links)
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or str(config.DB_PATH)

    async def full_audit(self) -> AuditReport:
        """Run a complete integrity audit.

        Returns AuditReport with all findings.
        """
        start = time.monotonic()
        report = AuditReport(
            timestamp=datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
        )

        try:
            async with connect_async_ctx(self._db_path) as db:
                db.row_factory = aiosqlite.Row

                # Get all facts ordered by ID
                async with db.execute(
                    "SELECT id, content, hash, prev_hash, signature, meta "
                    "FROM facts ORDER BY id ASC"
                ) as cursor:
                    facts = await cursor.fetchall()

                report.total_facts = len(facts)  # type: ignore[reportArgumentType]

                if not facts:
                    report.duration_seconds = time.monotonic() - start
                    return report

                # ── 1. Hash Chain Verification ──
                report.chain_status = await self._verify_chain(facts)  # type: ignore[reportArgumentType]

                # ── 2. Signature Verification ──
                sig_failures = await self._verify_signatures(facts)  # type: ignore[reportArgumentType]
                report.signature_failures = sig_failures
                report.facts_with_signatures = sum(1 for f in facts if f["signature"])
                report.facts_verified = report.facts_with_signatures - len(sig_failures)

        except ImportError:
            logger.error("aiosqlite not available — cannot run integrity audit")
            report.chain_status.is_valid = False
        except (OSError, ValueError, RuntimeError) as e:
            logger.error("Integrity audit failed: %s", e)
            report.chain_status.is_valid = False

        report.is_clean = report.chain_status.is_valid and len(report.signature_failures) == 0
        report.duration_seconds = time.monotonic() - start

        if not report.is_clean:
            logger.error(
                "🔴 INTEGRITY AUDIT FAILED: %d broken chains, %d signature failures",
                len(report.chain_status.broken_links),
                len(report.signature_failures),
            )
        else:
            logger.info(
                "✅ Integrity audit PASSED: %d facts verified in %.1fs",
                report.total_facts,
                report.duration_seconds,
            )

        return report

    async def verify_chain(self) -> ChainStatus:
        """Verify only the hash chain (quick check)."""
        try:
            async with connect_async_ctx(self._db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT id, content, hash, prev_hash FROM facts ORDER BY id ASC"
                ) as cursor:
                    facts = await cursor.fetchall()
                return await self._verify_chain(facts)  # type: ignore[reportArgumentType]
        except (OSError, ValueError, RuntimeError) as e:
            logger.error("Chain verification failed: %s", e)
            return ChainStatus(is_valid=False)

    async def verify_signatures(self) -> list[TamperedFact]:
        """Verify only Ed25519 signatures."""
        try:
            async with connect_async_ctx(self._db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT id, content, hash, signature FROM facts "
                    "WHERE signature IS NOT NULL AND signature != ''"
                ) as cursor:
                    facts = await cursor.fetchall()
                return await self._verify_signatures(facts)  # type: ignore[reportArgumentType]
        except (OSError, ValueError, RuntimeError) as e:
            logger.error("Signature verification failed: %s", e)
            return []

    # ── Internal Methods ──

    async def _verify_chain(self, facts: list[Any]) -> ChainStatus:
        """Verify SHA-256 hash chain continuity."""
        status = ChainStatus(total_facts=len(facts))

        if not facts:
            return status

        prev_hash: str | None = None
        hash_index: dict[str, int] = {}  # hash -> fact_id

        for fact in facts:
            self._verify_single_fact(fact, prev_hash, hash_index, status)
            prev_hash = fact["hash"] or ""

        self._detect_orphaned_facts(facts, hash_index, status)
        return status

    def _verify_single_fact(
        self, fact: Any, prev_hash: str | None, hash_index: dict[str, int], status: ChainStatus
    ) -> None:
        fact_id = fact["id"]
        content = fact["content"] or ""
        stored_hash = fact["hash"] or ""
        stored_prev = fact["prev_hash"] or ""

        # Compute expected hash
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Check hash integrity
        if stored_hash and stored_hash != expected_hash:
            status.broken_links.append(
                TamperedFact(
                    fact_id=fact_id,
                    issue="hash_mismatch",
                    expected=expected_hash[:16] + "...",
                    actual=stored_hash[:16] + "...",
                    content_preview=content[:50],
                )
            )
            status.is_valid = False

        # Check chain link
        if prev_hash is not None and stored_prev:
            if stored_prev != prev_hash:
                status.broken_links.append(
                    TamperedFact(
                        fact_id=fact_id,
                        issue="chain_break",
                        expected=prev_hash[:16] + "...",
                        actual=stored_prev[:16] + "...",
                        content_preview=content[:50],
                    )
                )
                status.is_valid = False

        # Track for orphan detection
        if stored_hash:
            hash_index[stored_hash] = fact_id
        status.verified += 1

    def _detect_orphaned_facts(
        self, facts: list[Any], hash_index: dict[str, int], status: ChainStatus
    ) -> None:
        # Detect orphaned facts (prev_hash points to non-existent fact)
        for fact in facts[1:]:  # Skip genesis fact
            stored_prev = fact["prev_hash"] or ""
            if stored_prev and stored_prev not in hash_index:
                status.orphaned_facts.append(
                    TamperedFact(
                        fact_id=fact["id"],
                        issue="orphaned_chain",
                        expected="existing_hash",
                        actual=stored_prev[:16] + "...",
                        content_preview=(fact["content"] or "")[:50],
                    )
                )
                status.is_valid = False

    async def _verify_signatures(self, facts: list[Any]) -> list[TamperedFact]:
        """Verify Ed25519 signatures on signed facts.

        When ``cortex_rs`` is available the entire batch is verified in Rust
        (GIL released), otherwise falls back to per-fact verification via the
        ``cryptography`` library.
        """
        failures: list[TamperedFact] = []

        try:
            from cortex.extensions.security.signatures import (
                SignatureVerificationError,
                get_default_signer,
            )
        except ImportError:
            logger.warning("Ed25519 signatures not available — skipping")
            return failures

        signer = get_default_signer()
        if not signer or not signer.can_verify:
            logger.info("No signing key configured — signature verification skipped")
            return failures

        # ── Rust batch path ──────────────────────────────────────────────────
        if _RUST_AVAILABLE and signer.public_key_b64:
            return self._verify_signatures_rust(facts, signer)

        # ── Pure-Python fallback ─────────────────────────────────────────────
        for fact in facts:
            self._verify_single_signature(fact, signer, failures, SignatureVerificationError)

        return failures

    def _verify_signatures_rust(self, facts: list[Any], signer: Any) -> list[TamperedFact]:
        """Batch-verify Ed25519 signatures using the Rust extension (GIL released)."""
        from cortex.extensions.security.signatures import _canonical_payload

        failures: list[TamperedFact] = []

        # Decode the signer's public key once.
        try:
            pub_key_bytes = base64.b64decode(signer.public_key_b64)
        except (ValueError, TypeError) as exc:
            logger.warning("Failed to decode public key for batch verification: %s", exc)
            return failures

        # Build parallel lists: messages, public_keys, signatures.
        valid_facts: list[Any] = []
        messages: list[bytes] = []
        public_keys: list[bytes] = []
        signatures: list[bytes] = []

        for fact in facts:
            sig_b64 = fact["signature"]
            if not sig_b64:
                continue
            fact_hash = fact["hash"] or ""
            content = fact["content"] or ""
            try:
                sig_bytes = base64.b64decode(sig_b64)
                payload = _canonical_payload(content, fact_hash)
            except (ValueError, TypeError):
                # Malformed base64 — record as failure immediately.
                failures.append(
                    TamperedFact(
                        fact_id=fact["id"],
                        issue="signature_invalid",
                        expected="valid_ed25519",
                        actual="MALFORMED_BASE64",
                        content_preview=content[:50],
                    )
                )
                continue

            valid_facts.append(fact)
            messages.append(payload)
            public_keys.append(pub_key_bytes)
            signatures.append(sig_bytes)

        if not valid_facts:
            return failures

        try:
            results = _cortex_rs.verify_ed25519_batch(messages, public_keys, signatures)
        except (ValueError, RuntimeError) as exc:
            logger.warning("Rust batch verification failed, falling back per-fact: %s", exc)
            # Graceful degradation: verify individually using the Python signer.
            from cortex.extensions.security.signatures import SignatureVerificationError

            for fact in valid_facts:
                self._verify_single_signature(
                    fact, signer, failures, SignatureVerificationError
                )
            return failures

        for fact, is_valid in zip(valid_facts, results, strict=False):
            if not is_valid:
                content = fact["content"] or ""
                failures.append(
                    TamperedFact(
                        fact_id=fact["id"],
                        issue="signature_invalid",
                        expected="valid_ed25519",
                        actual="FAILED",
                        content_preview=content[:50],
                    )
                )

        return failures

    def _verify_single_signature(
        self, fact: Any, signer: Any, failures: list[TamperedFact], ErrorClass: type[Exception]
    ) -> None:
        sig = fact["signature"]
        if not sig:
            return

        fact_hash = fact["hash"] or ""
        content = fact["content"] or ""

        try:
            signer.verify(content, fact_hash, sig)
        except ErrorClass:
            failures.append(
                TamperedFact(
                    fact_id=fact["id"],
                    issue="signature_invalid",
                    expected="valid_ed25519",
                    actual="FAILED",
                    content_preview=content[:50],
                )
            )
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning("Signature check error for fact %d: %s", fact["id"], e)


# Convenience function
async def quick_audit() -> AuditReport:
    """Run a quick integrity audit with default settings."""
    auditor = IntegrityAuditor()
    return await auditor.full_audit()
