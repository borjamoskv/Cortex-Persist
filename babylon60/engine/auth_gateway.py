import json
import logging
import sqlite3
import time
import uuid
from typing import Any

logger = logging.getLogger("babylon60.engine.auth_gateway")


class QuorumGateway:
    """
    Byzantine-Aware Retrieval Transition Gateway.
    Implements f < n/3 BFT consensus using multi-signature threshold validation.
    """

    def __init__(self, engine: Any, n_nodes: int = 4, f_nodes: int = 1):
        self.engine = engine
        self.n = n_nodes
        self.f = f_nodes
        self.threshold = self.n - self.f

    async def ensure_table(self) -> None:
        """Ensures the quorum_requests table exists in the DB."""
        try:
            conn = self.engine.pool.get_connection()
            conn.execute(
                """CREATE TABLE IF NOT EXISTS quorum_requests (
                    id TEXT PRIMARY KEY,
                    hypothesis TEXT,
                    state_payload TEXT,
                    status TEXT,
                    created_at REAL,
                    resolved_at REAL,
                    signatures_json TEXT
                )"""
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to ensure quorum_requests table: %s", e)

    async def request_override(self, hypothesis: str, state: dict[str, Any]) -> str:
        """
        Creates an authorization request for the Quorum.
        Returns the Request ID.
        """
        req_id = f"QRM-{str(uuid.uuid4())[:8].upper()}"
        logger.info("[QuorumGateway] Issuing BFT Consensus Request: %s", req_id)

        try:
            conn = self.engine.pool.get_connection()
            conn.execute(
                """INSERT INTO quorum_requests (id, hypothesis, state_payload, status, created_at, signatures_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (req_id, hypothesis, json.dumps(state), "PENDING", time.monotonic(), "[]"),
            )
            conn.commit()
            logger.warning(
                "[QuorumGateway] Action suspended. Awaiting %d votes to reach quorum for %s",
                self.threshold,
                req_id,
            )
        except sqlite3.Error as e:
            logger.error("[QuorumGateway] DB insert failed: %s", e)

        return req_id

    async def submit_vote(
        self, req_id: str, signature_b64: str, public_key_b64: str, semantic_truth: bool = True
    ) -> bool:
        """
        Submits a cryptographic vote.
        In a real scenario, semantic_truth is evaluated by the node before calling this.
        If semantic_truth is False, the honest node should reject or not vote.
        """
        if not semantic_truth:
            logger.warning(
                "[QuorumGateway] Honest node evaluated payload as CORRUPT. Withholding vote."
            )
            return False

        try:
            from babylon60.extensions.security.signatures import (
                Ed25519Signer,
                SignatureVerificationError,
            )

            conn = self.engine.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, state_payload, signatures_json FROM quorum_requests WHERE id = ?",
                (req_id,),
            )
            row = cursor.fetchone()

            if not row:
                logger.error("[QuorumGateway] Request %s not found.", req_id)
                return False

            status, state_payload, sigs_json = row

            if status != "PENDING":
                logger.warning("[QuorumGateway] Request %s is already %s.", req_id, status)
                return False

            # C5-REAL Cryptographic Verification
            signer = Ed25519Signer(public_key_bytes=None)

            try:
                signer.verify(
                    content=state_payload,
                    fact_hash=req_id,
                    signature_b64=signature_b64,
                    public_key_b64=public_key_b64,
                )
                logger.info("[QuorumGateway] Ed25519 Signature Verified for %s", req_id)
            except (SignatureVerificationError, ValueError, TypeError, RuntimeError):
                logger.error(
                    "[QuorumGateway] CRITICAL: Cryptographic Verification Failed for %s. Discarding vote.",
                    req_id,
                )
                return False

            signatures: list[dict[str, str]] = json.loads(sigs_json)

            # Prevent double voting
            if any(sig["public_key"] == public_key_b64 for sig in signatures):
                logger.warning("[QuorumGateway] Node %s already voted.", public_key_b64[:8])
                return False

            signatures.append({"signature": signature_b64, "public_key": public_key_b64})
            new_sigs_json = json.dumps(signatures)

            vote_count = len(signatures)

            if vote_count >= self.threshold:
                conn.execute(
                    "UPDATE quorum_requests SET status = 'QUORUM_REACHED', resolved_at = ?, signatures_json = ? WHERE id = ?",
                    (time.monotonic(), new_sigs_json, req_id),
                )
                logger.info(
                    "[QuorumGateway] Request %s REACHED QUORUM (%d/%d). BFT Consensus Achieved.",
                    req_id,
                    vote_count,
                    self.threshold,
                )
            else:
                conn.execute(
                    "UPDATE quorum_requests SET signatures_json = ? WHERE id = ?",
                    (new_sigs_json, req_id),
                )
                logger.info(
                    "[QuorumGateway] Vote registered for %s (%d/%d).",
                    req_id,
                    vote_count,
                    self.threshold,
                )

            conn.commit()
            return True
        except (sqlite3.Error, ValueError) as e:
            logger.error("[QuorumGateway] Failed to submit vote for request %s: %s", req_id, e)
            return False

    async def reject_request(self, req_id: str) -> bool:
        """Rejects a request directly (fallback/admin override)."""
        try:
            conn = self.engine.pool.get_connection()
            conn.execute(
                "UPDATE quorum_requests SET status = 'REJECTED', resolved_at = ? WHERE id = ?",
                (time.monotonic(), req_id),
            )
            conn.commit()
            logger.info("[QuorumGateway] Request %s REJECTED.", req_id)
            return True
        except sqlite3.Error as e:
            logger.error("[QuorumGateway] Failed to reject request %s: %s", req_id, e)
            return False

    async def check_timeout(self, req_id: str, timeout_s: float) -> bool:
        """
        Checks if the request has expired (incomplete quorum within timeout).
        If expired, marks status as 'TIMEOUT_EXPIRED' and returns True.
        """
        try:
            conn = self.engine.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT status, created_at FROM quorum_requests WHERE id = ?", (req_id,))
            row = cursor.fetchone()
            if not row:
                return False
            status, created_at = row
            if status == "PENDING" and (time.monotonic() - created_at) > timeout_s:
                conn.execute(
                    "UPDATE quorum_requests SET status = 'TIMEOUT_EXPIRED', resolved_at = ? WHERE id = ?",
                    (time.monotonic(), req_id),
                )
                conn.commit()
                logger.warning("[QuorumGateway] Request %s failed due to timeout.", req_id)
                return True
            return False
        except sqlite3.Error as e:
            logger.error("[QuorumGateway] Failed checking timeout for %s: %s", req_id, e)
            return False
