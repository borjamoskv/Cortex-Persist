# [C5-REAL] Exergy-Maximized
"""
T-Cell Daemon: IHELP / David Dominguez Anergy Purge

This sovereign daemon binds to the MHCAntigenRouter. Its sole purpose is to
phagocytize payloads containing the structural signatures of the Substack Mafia
('ihelp', 'david dominguez'), calculating the saved exergy and emitting a
cryptographic rejection to the CORTEX Master Ledger.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Final, Optional

# Import the router from the engine
from babylon60.engine.causal.taint_engine import MHCAntigenRouter, canonicalize_content

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("babylon60.daemon.t_cell_ihelp")


class IHelpPurgeDaemon:
    """
    Sovereign T-Cell monitoring daemon targeting anergy vectors.
    """

    MAX_PAYLOAD_BYTES: Final[int] = 1_048_576  # 1 MB Safety Threshold

    def __init__(self, mhc_router: MHCAntigenRouter) -> None:
        self.agent_id: Final[str] = "t_cell_alpha_purge"
        self.mhc_router: MHCAntigenRouter = mhc_router

        # Import dynamically to avoid circular dependencies
        from babylon60.routes.telemetry import BASE_MAFIA_NODES

        # Escape all regex characters in the nodes, and convert whitespace in nodes to \s+
        escaped_nodes: list[str] = []
        for node in BASE_MAFIA_NODES:
            escaped: str = re.escape(node)
            cleaned: str = re.sub(r"(\\ )|\s+", r"\\s+", escaped)
            escaped_nodes.append(cleaned)

        # Regex signature targeting the specific Anergy vectors
        pattern: str = "|".join(escaped_nodes)
        self.antigen_signature: Final[str] = rf"(?i)\b({pattern})\b"

        # Bind the daemon to the MHC router
        self.mhc_router.register_t_cell(self.agent_id, self.antigen_signature)
        logger.info(
            f"[{self.agent_id}] Armed and actively monitoring Swarm ingest paths for {self.antigen_signature}."
        )

    async def _ensure_agent_registered(self, conn: aiosqlite.Connection, pub_key: str) -> None:
        """
        Garantiza que la identidad soberana del Daemon esté registrada en la tabla agents.
        """
        import sqlite3

        from babylon60.database.core import causal_write

        row: Optional[tuple[str]] = None
        try:
            async with conn.execute(
                "SELECT id FROM agents WHERE id = ?", (self.agent_id,)
            ) as cursor:
                row = await cursor.fetchone()
        except sqlite3.OperationalError:
            # Create agents table if missing
            from babylon60.database.schema_extensions import CREATE_AGENTS

            with causal_write(conn):
                await conn.execute(CREATE_AGENTS)
                await conn.commit()

        if not row:
            with causal_write(conn):
                await conn.execute(
                    "INSERT INTO agents (id, public_key, name, agent_type, tenant_id) VALUES (?, ?, ?, ?, ?)",
                    (self.agent_id, pub_key, self.agent_id, "daemon", "global"),
                )
                await conn.commit()

    async def _update_daemon_reputation(self, conn: aiosqlite.Connection, is_hit: bool) -> None:
        """
        Actualiza asintóticamente la reputación del agente de acuerdo con hits/misses de alineación.
        """
        from babylon60.database.core import causal_write

        async with conn.execute(
            "SELECT reputation_score, alignment_hits, alignment_misses FROM agents WHERE id = ?",
            (self.agent_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return

        current_rep: float = row[0]
        hits: int = row[1]
        misses: int = row[2]

        if is_hit:
            hits += 1
            new_rep: float = min(1.0, current_rep + 0.05 * (1.0 - current_rep))
            query: str = (
                "UPDATE agents SET reputation_score = ?, alignment_hits = ?, last_active_at = ? WHERE id = ?"
            )
            params: tuple[float, int, str, str] = (
                new_rep,
                hits,
                datetime.now(timezone.utc).isoformat(),
                self.agent_id,
            )
        else:
            misses += 1
            new_rep = max(0.0, current_rep * 0.95)
            query = (
                "UPDATE agents SET reputation_score = ?, alignment_misses = ?, last_active_at = ? WHERE id = ?"
            )
            params = (
                new_rep,
                misses,
                datetime.now(timezone.utc).isoformat(),
                self.agent_id,
            )

        with causal_write(conn):
            await conn.execute(query, params)
            await conn.commit()

    async def phagocytize(self, payload: str, source_agent: str) -> dict[str, Any]:
        """
        Activated when the MHC router presents a matching antigen.
        Calculates Exergy saved, drops the payload, and logs the execution.
        """
        import os
        import uuid

        from babylon60.audit.ledger import EnterpriseAuditLedger
        from babylon60.crypto.keys import KeyManager
        from babylon60.database.core import connect_async
        from babylon60.engine.causal.taint_engine import generate_secure_taint_token

        # Auto-defense check against denial-of-service payload attacks
        if len(payload) > self.MAX_PAYLOAD_BYTES:
            logger.warning(
                f"[{self.agent_id}] Payload size ({len(payload)} bytes) exceeds threshold. Truncating payload."
            )
            payload = payload[: self.MAX_PAYLOAD_BYTES] + "\n[TRUNCATED_BY_ANTIGEN_GUARD]"

        canonical: bytes = canonicalize_content(payload)
        waste_bytes: int = len(canonical)
        payload_hash: str = hashlib.sha3_256(canonical).hexdigest()

        # Calculate theoretical compute cycles saved (Anergy eliminated)
        # Assuming ~4 tokens per word, 1 token ~ 3 bytes
        tokens_saved: int = waste_bytes // 3

        logger.warning(
            f"[{self.agent_id}] 🛑 ANERGY DETECTED 🛑\n"
            f"Source: {source_agent}\n"
            f"Antigen Hash: {payload_hash[:16]}\n"
            f"Thermodynamic Action: Payload obliterated. Saved {waste_bytes} bytes ({tokens_saved} tokens) of GC/LLM evaluation overhead."
        )

        db_path: str = (
            os.environ.get("CORTEX_DB_PATH") or os.path.expanduser("~/.cortex/cortex.db")
        )
        conn = await connect_async(db_path)
        try:
            # Initialize EnterpriseAuditLedger
            ledger = EnterpriseAuditLedger(conn)
            await ledger.ensure_table()

            # Check and register agent identity
            km = KeyManager(service_name="cortex_agents")
            pub_key: Optional[str] = km.get_public_key_b64(self.agent_id)
            if not pub_key:
                pub_key = km.generate_and_store_key(self.agent_id)

            await self._ensure_agent_registered(conn, pub_key)

            # Generate secure CORTEX-TAINT signature token
            session_id: str = "session_" + uuid.uuid4().hex[:16]
            priv_key_b64: Optional[str] = km.get_private_key_b64(self.agent_id)
            if not priv_key_b64:
                raise ValueError(f"Private key for actor {self.agent_id} not found.")
            taint_token: str = generate_secure_taint_token(
                agent_id=self.agent_id,
                session_id=session_id,
                content=payload,
                private_key_b64=priv_key_b64,
            )

            # Write PHAGOCYTOSIS to Master Ledger
            await ledger.log_action(
                tenant_id="global",
                actor_role="daemon",
                actor_id=self.agent_id,
                action="PHAGOCYTOSIS",
                resource=taint_token,
                status="SUCCESS",
            )

            # Update daemon reputation (Success hit)
            await self._update_daemon_reputation(conn, is_hit=True)
        except Exception as ex:  # noqa: BLE001
            logger.error(f"[{self.agent_id}] Failed during phagocytosis transaction: {ex}")
            raise ex
        finally:
            await conn.close()

        # Emit to Master Ledger (C5-REAL Proof of Work)
        audit_trail: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "PHAGOCYTOSIS",
            "antigen_type": "SUBSTACK_MAFIA_IHELP",
            "source_agent": source_agent,
            "hash_destroyed": payload_hash,
            "exergy_metrics": {"bytes_saved": waste_bytes, "tokens_saved": tokens_saved},
            "taint_token": taint_token,
        }

        return audit_trail

    async def scan_telemetry_targets(self) -> dict[str, Any]:
        """
        Executes concurrent checks of all Mafia domains in BASE_MAFIA_NODES.
        """
        import asyncio
        import os

        import httpx

        from babylon60.audit.ledger import EnterpriseAuditLedger
        from babylon60.database.core import connect_async
        from babylon60.routes.telemetry import BASE_MAFIA_NODES

        # Filter out non-domains (e.g. names with spaces or no dots)
        domains: list[str] = [
            node for node in BASE_MAFIA_NODES if "." in node and " " not in node
        ]

        db_path: str = (
            os.environ.get("CORTEX_DB_PATH") or os.path.expanduser("~/.cortex/cortex.db")
        )
        conn = await connect_async(db_path)
        try:
            ledger = EnterpriseAuditLedger(conn)
            await ledger.ensure_table()

            # Ensure daemon registration on startup check
            from babylon60.crypto.keys import KeyManager

            km = KeyManager(service_name="cortex_agents")
            pub_key = km.get_public_key_b64(self.agent_id) or km.generate_and_store_key(
                self.agent_id
            )
            await self._ensure_agent_registered(conn, pub_key)

            semaphore: asyncio.Semaphore = asyncio.Semaphore(50)

            async def check_domain(hostname: str) -> None:
                async with semaphore:
                    try:
                        # 1. DNS check
                        await asyncio.get_running_loop().getaddrinfo(hostname, None)

                        # 2. HTTP and RSS check
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            # HTTP check
                            await client.get(f"https://{hostname}")

                            # RSS feed validation check
                            feed_content: Optional[str] = None
                            for path in ["/feed", "/rss"]:
                                try:
                                    resp = await client.get(f"https://{hostname}{path}")
                                    if resp.status_code == 200:
                                        feed_content = resp.text
                                        break
                                except OSError:
                                    continue

                            if feed_content and re.search(self.antigen_signature, feed_content):
                                # Trigger phagocytosis
                                await self.phagocytize(
                                    feed_content, source_agent=f"rss_feed:{hostname}"
                                )

                    except Exception as e:  # noqa: BLE001
                        logger.error(
                            f"[{self.agent_id}] Domain checkout failed for {hostname}: {e}"
                        )
                        # Log FORENSIC_ANOMALY to Master Ledger
                        await ledger.log_action(
                            tenant_id="global",
                            actor_role="system",
                            actor_id=self.agent_id,
                            action="FORENSIC_ANOMALY",
                            resource=hostname,
                            status="ANOMALY",
                        )
                        # Penalize agent reputation on telemetry anomaly
                        await self._update_daemon_reputation(conn, is_hit=False)

            await asyncio.gather(*(check_domain(d) for d in domains))
        finally:
            await conn.close()

        return {"status": "completed", "checked_domains": len(domains)}


# Initialization hook for daemon loader
def init_daemon(mhc_router: MHCAntigenRouter) -> IHelpPurgeDaemon:
    return IHelpPurgeDaemon(mhc_router)
