# [C5-REAL] Exergy-Maximized
"""
T-Cell Daemon: IHELP / David Dominguez Anergy Purge

This sovereign daemon binds to the MHCAntigenRouter. Its sole purpose is to
phagocytize payloads containing the structural signatures of the Substack Mafia
('ihelp', 'david dominguez'), calculating the saved exergy and emitting a
cryptographic rejection to the CORTEX Master Ledger.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone

# Import the existing router from the engine
from cortex.engine.causal.taint_engine import MHCAntigenRouter, canonicalize_content

logger = logging.getLogger("cortex.daemon.t_cell_ihelp")


class IHelpPurgeDaemon:
    def __init__(self, mhc_router: MHCAntigenRouter):
        self.agent_id = "t_cell_alpha_purge"
        self.mhc_router = mhc_router

        # Import dynamically to avoid circular dependencies
        from cortex.routes.telemetry import BASE_MAFIA_NODES

        # Escape all regex characters in the nodes, and convert whitespace in nodes to \s+
        escaped_nodes = []
        for node in BASE_MAFIA_NODES:
            escaped = re.escape(node)
            cleaned = re.sub(r'(\\ )|\s+', r'\\s+', escaped)
            escaped_nodes.append(cleaned)

        # Regex signature targeting the specific Anergy vectors
        pattern = "|".join(escaped_nodes)
        self.antigen_signature = rf"(?i)\b({pattern})\b"

        # Bind the daemon to the MHC router
        self.mhc_router.register_t_cell(self.agent_id, self.antigen_signature)
        logger.info(
            f"[{self.agent_id}] Armed and actively monitoring Swarm ingest paths for {self.antigen_signature}."
        )

    async def phagocytize(self, payload: str, source_agent: str) -> dict:
        """
        Activated when the MHC router presents a matching antigen.
        Calculates Exergy saved, drops the payload, and logs the execution.
        """
        import os
        import sqlite3
        import uuid

        from cortex.audit.ledger import EnterpriseAuditLedger
        from cortex.crypto.keys import KeyManager
        from cortex.database.core import connect_async
        from cortex.engine.causal.taint_engine import generate_secure_taint_token

        canonical = canonicalize_content(payload)
        waste_bytes = len(canonical)
        payload_hash = hashlib.sha3_256(canonical).hexdigest()

        # Calculate theoretical compute cycles saved (Anergy eliminated)
        # Assuming ~4 tokens per word, 1 token ~ 3 bytes
        tokens_saved = waste_bytes // 3

        logger.warning(
            f"[{self.agent_id}] 🛑 ANERGY DETECTED 🛑\n"
            f"Source: {source_agent}\n"
            f"Antigen Hash: {payload_hash[:16]}\n"
            f"Thermodynamic Action: Payload obliterated. Saved {waste_bytes} bytes ({tokens_saved} tokens) of GC/LLM evaluation overhead."
        )

        db_path = os.environ.get("CORTEX_DB_PATH") or os.path.expanduser("~/.cortex/cortex.db")
        conn = await connect_async(db_path)
        try:
            # Initialize EnterpriseAuditLedger
            ledger = EnterpriseAuditLedger(conn)
            await ledger.ensure_table()

            # Check and register agent identity
            km = KeyManager(service_name="cortex_agents")
            pub_key = km.get_public_key_b64(self.agent_id)
            if not pub_key:
                pub_key = km.generate_and_store_key(self.agent_id)

            # Ensure agents table exists and contains the agent_id
            from cortex.database.core import causal_write

            row = None
            try:
                async with conn.execute("SELECT id FROM agents WHERE id = ?", (self.agent_id,)) as cursor:
                    row = await cursor.fetchone()
            except sqlite3.OperationalError:
                # Create agents table if missing
                from cortex.database.schema_extensions import CREATE_AGENTS
                with causal_write(conn):
                    await conn.execute(CREATE_AGENTS)
                    await conn.commit()

            if not row:
                with causal_write(conn):
                    await conn.execute(
                        "INSERT INTO agents (id, public_key, name, agent_type, tenant_id) VALUES (?, ?, ?, ?, ?)",
                        (self.agent_id, pub_key, self.agent_id, "daemon", "global")
                    )
                    await conn.commit()

            # Generate secure CORTEX-TAINT signature token
            session_id = "session_" + uuid.uuid4().hex[:16]
            priv_key_b64 = km.get_private_key_b64(self.agent_id)
            if not priv_key_b64:
                raise ValueError(f"Private key for actor {self.agent_id} not found.")
            taint_token = generate_secure_taint_token(
                agent_id=self.agent_id,
                session_id=session_id,
                content=payload,
                private_key_b64=priv_key_b64
            )

            # Write PHAGOCYTOSIS to Master Ledger
            await ledger.log_action(
                tenant_id="global",
                actor_role="daemon",
                actor_id=self.agent_id,
                action="PHAGOCYTOSIS",
                resource=taint_token,
                status="SUCCESS"
            )
        finally:
            await conn.close()

        # Emit to Master Ledger (C5-REAL Proof of Work)
        audit_trail = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "PHAGOCYTOSIS",
            "antigen_type": "SUBSTACK_MAFIA_IHELP",
            "source_agent": source_agent,
            "hash_destroyed": payload_hash,
            "exergy_metrics": {"bytes_saved": waste_bytes, "tokens_saved": tokens_saved},
            "taint_token": taint_token,
        }

        return audit_trail

    async def scan_telemetry_targets(self) -> dict:
        """
        Executes concurrent checks of all Mafia domains in BASE_MAFIA_NODES.
        """
        import asyncio
        import os

        import httpx

        from cortex.audit.ledger import EnterpriseAuditLedger
        from cortex.database.core import connect_async
        from cortex.routes.telemetry import BASE_MAFIA_NODES

        # Filter out non-domains (e.g. names with spaces or no dots)
        domains = [node for node in BASE_MAFIA_NODES if "." in node and " " not in node]

        db_path = os.environ.get("CORTEX_DB_PATH") or os.path.expanduser("~/.cortex/cortex.db")
        conn = await connect_async(db_path)
        ledger = EnterpriseAuditLedger(conn)
        await ledger.ensure_table()

        semaphore = asyncio.Semaphore(50)

        async def check_domain(hostname: str):
            async with semaphore:
                try:
                    # 1. DNS check
                    await asyncio.get_running_loop().getaddrinfo(hostname, None)

                    # 2. HTTP and RSS check
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        # HTTP check
                        await client.get(f"https://{hostname}")

                        # RSS feed validation check
                        feed_content = None
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
                            await self.phagocytize(feed_content, source_agent=f"rss_feed:{hostname}")

                except Exception as e:
                    logger.error(f"[{self.agent_id}] Domain checkout failed for {hostname}: {e}")
                    # Log FORENSIC_ANOMALY to Master Ledger
                    await ledger.log_action(
                        tenant_id="global",
                        actor_role="system",
                        actor_id=self.agent_id,
                        action="FORENSIC_ANOMALY",
                        resource=hostname,
                        status="ANOMALY"
                    )

        try:
            await asyncio.gather(*(check_domain(d) for d in domains))
        finally:
            await conn.close()

        return {"status": "completed", "checked_domains": len(domains)}


# Initialization hook for daemon loader
def init_daemon(mhc_router: MHCAntigenRouter):
    return IHelpPurgeDaemon(mhc_router)
