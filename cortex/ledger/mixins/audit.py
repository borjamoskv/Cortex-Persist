# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass
from cortex.ledger.merkle import MerkleTree
from cortex.utils.canonical import compute_tx_hash, compute_tx_hash_v1, now_iso

logger = logging.getLogger("cortex.ledger")


class LedgerAuditMixin:
    async def audit_integrity_async(self, tenant_id: str | None = None) -> dict:
        """Perform a full integrity audit asynchronously (Ω₁)."""
        violations = []
        tx_count = 0
        async with self._get_conn_proxy() as conn:
            started_at = now_iso()

            # 1. Verify transaction chain
            (
                chain_violations,
                tx_count,
                store_txs_to_verify,
                purged_store_tx_ids,
            ) = await self._verify_chain(conn, tenant_id)
            violations.extend(chain_violations)

            # 2. Verify facts
            facts_violations = await self._verify_facts(
                conn, tenant_id, store_txs_to_verify, purged_store_tx_ids
            )
            violations.extend(facts_violations)

            # 3. Verify Merkle roots
            merkle_violations = await self._verify_merkle_roots(conn, tenant_id)
            violations.extend(merkle_violations)

            # Finalize audit record
            status = "ok" if not violations else "violation"
            from cortex.database.core import causal_write
            with causal_write(conn):
                await conn.execute(
                    "INSERT INTO integrity_checks (check_type, status, details, started_at, completed_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        "full" if tenant_id is None else "tenant",
                        status,
                        json.dumps(violations),
                        started_at,
                        now_iso(),
                    ),
                )
            await conn.commit()
        return {"valid": not violations, "violations": violations, "tx_count": tx_count}

    async def _verify_chain(
        self, conn, tenant_id: str | None
    ) -> tuple[list[dict], int, dict[int, str], set[int]]:
        violations = []
        tx_count = 0
        expected_prev_by_tenant: dict[str, str] = {}
        expected_prev_global = "GENESIS"
        store_txs_to_verify: dict[int, str] = {}
        purged_store_tx_ids: set[int] = set()

        cursor = await conn.execute(
            "SELECT id, COALESCE(tenant_id, 'default'), project, action, detail, prev_hash, hash, timestamp FROM transactions ORDER BY id"
        )
        while True:
            row = await cursor.fetchone()
            if not row:
                break
            tid, tx_tenant_id, proj, act, det, prev, h, ts = row
            expected_prev = expected_prev_by_tenant.get(tx_tenant_id, "GENESIS")

            if tenant_id is None or tx_tenant_id == tenant_id:
                tx_count += 1
                computed_v3 = compute_tx_hash(prev, proj, act, det, ts, tenant_id=tx_tenant_id)
                computed_v2 = compute_tx_hash(prev, proj, act, det, ts)
                computed_v1 = compute_tx_hash_v1(prev, proj, act, det, ts)

                if computed_v3 == h and prev != expected_prev:
                    violations.append({"id": tid, "type": "CHAIN_BREAK", "expected": expected_prev})
                elif h in {computed_v2, computed_v1} and prev != expected_prev_global:
                    violations.append(
                        {
                            "id": tid,
                            "type": "CHAIN_BREAK",
                            "expected": expected_prev,
                            "legacy_expected": expected_prev_global,
                        }
                    )
                elif computed_v3 != h and h not in {computed_v2, computed_v1}:
                    violations.append({"id": tid, "type": "TAMPER_DETECTED", "stored": h})

                try:
                    detail = json.loads(det) if det else {}
                except Exception as e:
                    logger.debug("Failed to parse transaction detail json for tx %s: %s", tid, e)
                    detail = {}

                if act == "store":
                    c_hash = detail.get("content_hash")
                    if c_hash:
                        store_txs_to_verify[tid] = c_hash
                elif act == "purge":
                    p_store_tx_id = detail.get("store_tx_id")
                    if p_store_tx_id is not None:
                        purged_store_tx_ids.add(int(p_store_tx_id))

            # Update running expectations at the END of the loop
            expected_prev_by_tenant[tx_tenant_id] = h
            expected_prev_global = h

            if tid % 100 == 0:
                await asyncio.sleep(0)

        return violations, tx_count, store_txs_to_verify, purged_store_tx_ids

    async def _verify_facts(
        self,
        conn,
        tenant_id: str | None,
        store_txs_to_verify: dict[int, str],
        purged_store_tx_ids: set[int],
    ) -> list[dict]:
        violations = []
        cursor_check = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='facts'"
        )
        facts_table_exists = await cursor_check.fetchone() is not None
        await cursor_check.close()

        if not facts_table_exists:
            return violations

        active_facts_by_tx: dict[int, dict[str, Any]] = {}
        if tenant_id is None:
            fact_cursor = await conn.execute(
                "SELECT tx_id, content, hash, COALESCE(tenant_id, 'default') FROM facts"
            )
        else:
            fact_cursor = await conn.execute(
                "SELECT tx_id, content, hash, COALESCE(tenant_id, 'default') FROM facts WHERE tenant_id = ?",
                (tenant_id,),
            )

        while True:
            f_row = await fact_cursor.fetchone()
            if not f_row:
                break
            f_tx_id, f_content, f_hash, f_tenant_id = f_row
            if f_tx_id is not None:
                active_facts_by_tx[f_tx_id] = {
                    "content": f_content,
                    "hash": f_hash,
                    "tenant_id": f_tenant_id,
                }
        await fact_cursor.close()

        from cortex.crypto import get_default_encrypter
        from cortex.utils.canonical import compute_fact_hash

        enc = get_default_encrypter()
        for f_tx_id, info in list(active_facts_by_tx.items()):
            try:
                decrypted = enc.decrypt_str(info["content"], tenant_id=info["tenant_id"])
                computed_hash = compute_fact_hash(decrypted)
                if computed_hash != info["hash"]:
                    violations.append(
                        {
                            "id": f_tx_id,
                            "type": "FACT_HASH_MISMATCH",
                            "stored_hash": info["hash"],
                            "computed_hash": computed_hash,
                        }
                    )
            except Exception as e:
                violations.append(
                    {"id": f_tx_id, "type": "FACT_DECRYPTION_FAILED", "error": str(e)}
                )

        for store_tid, expected_hash in store_txs_to_verify.items():
            if store_tid in active_facts_by_tx:
                fact_hash = active_facts_by_tx[store_tid]["hash"]
                if fact_hash != expected_hash:
                    violations.append(
                        {
                            "id": store_tid,
                            "type": "FACT_MUTATION_DETECTED",
                            "expected_hash": expected_hash,
                            "fact_hash": fact_hash,
                        }
                    )
            elif store_tid not in purged_store_tx_ids:
                violations.append(
                    {"id": store_tid, "type": "FACT_MISSING", "expected_hash": expected_hash}
                )

        return violations

    async def _verify_merkle_roots(self, conn, tenant_id: str | None) -> list[dict]:
        violations = []
        if tenant_id is None:
            cursor = await conn.execute(
                "SELECT COALESCE(tenant_id, 'default'), root_hash, tx_start_id, tx_end_id FROM merkle_roots"
            )
        else:
            cursor = await conn.execute(
                "SELECT COALESCE(tenant_id, 'default'), root_hash, tx_start_id, tx_end_id FROM merkle_roots WHERE tenant_id = ?",
                (tenant_id,),
            )
        roots = list(await cursor.fetchall())
        for root_tenant_id, stored_root, start, end in roots:
            if root_tenant_id == "__global__":
                c = await conn.execute(
                    "SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id",
                    (start, end),
                )
            else:
                c = await conn.execute(
                    "SELECT hash FROM transactions WHERE tenant_id = ? AND id >= ? AND id <= ? ORDER BY id",
                    (root_tenant_id, start, end),
                )
            hashes = [r[0] for r in list(await c.fetchall())]
            computed_root = MerkleTree(hashes).root_hash
            if computed_root != stored_root:
                violations.append({"range": f"{start}-{end}", "type": "MERKLE_MISMATCH"})
        return violations
