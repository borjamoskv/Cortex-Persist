# [C5-REAL] Exergy-Maximized
"""
C5-REAL Epistemic Store.
Replaces the stochastic `fact_store_core` with deterministic EDG insertions.
All mutations are routed through the MTKGuard. No raw SQLite inserts allowed.
"""

import json
import logging
import time

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

from babylon60.engine.mtk_core import MTKGuard
from babylon60.types.evidence import ClosurePayload

logger = logging.getLogger(__name__)


async def ingest_c5_node(
    conn: aiosqlite.Connection,
    tenant_id: str,
    payload: ClosurePayload,
    status: str,
    confidence_b60: int,
    exergy_cost: int,
    agent_id: str,
    mtk_guard: MTKGuard,
) -> str:
    """
    Ingests a node into the Epistemic Directed Graph (EDG).
    This MUST be wrapped in `mtk_guard.transaction_boundary` to pass physical authorizer constraints.
    """
    if status not in ("Proven", "Inferred", "Speculative", "Contradicted"):
        raise ValueError(f"Invalid epistemic status: {status}")

    # Generate Node ID and Ledger Hash
    node_id = payload.payload_hash
    b60_timestamp = time.time_ns() // 1_000_000  # ms precision

    async with mtk_guard.transaction_boundary(payload) as _token:
        # Generate strict ledger entry
        ledger_hash = payload.canonical_hash() if hasattr(payload, "canonical_hash") else payload.payload_hash
        
        # INSERT into Master Ledger
        cursor = await conn.execute(
            """
            INSERT INTO c5_audit_ledger 
            (ledger_hash, prev_hash, agent_id, action_type, payload_sig, b60_timestamp, b60_exergy_cost, is_sealed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ledger_hash,
                "GENESIS",  # In a real system, fetch latest hash from ledger
                agent_id,
                "EDG_MUTATION",
                payload.signature if hasattr(payload, "signature") else "unsigned",
                b60_timestamp,
                exergy_cost,
                1
            )
        )
        ledger_seq = cursor.lastrowid

        # INSERT into EDG Nodes
        import dataclasses
        serialized_payload = json.dumps(dataclasses.asdict(payload), default=str)

        await conn.execute(
            """
            INSERT INTO c5_edg_nodes
            (node_id, ledger_seq, status, b60_confidence, b60_exergy, node_schema, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node_id,
                ledger_seq,
                status,
                confidence_b60,
                exergy_cost,
                payload.schema_hash if hasattr(payload, "schema_hash") else "v1.0",
                serialized_payload
            )
        )

        # INSERT into Memory Vault
        # Encrypt the payload here (Author: Borja Moskv)
        from babylon60.crypto import get_default_encrypter
        encrypter = get_default_encrypter()
        encrypted_blob = encrypter.encrypt_str(serialized_payload, tenant_id=tenant_id)
        
        await conn.execute(
            """
            INSERT INTO c5_memory_vault
            (vault_id, tenant_id, node_id, ledger_seq, b60_timestamp, is_active, encrypted_blob, taint_flag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"vault_{node_id}",
                tenant_id,
                node_id,
                ledger_seq,
                b60_timestamp,
                1,
                encrypted_blob,
                "CORTEX-TAINT"
            )
        )

        await conn.commit()
        logger.info(f"[C5-REAL] Epistemic Node {node_id} ingested via MTK Gate 1.")
        return node_id
