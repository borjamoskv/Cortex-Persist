# [C5-REAL] Exergy-Maximized
"""
MOSKV-AEGIS: The Proprietary C4-SIM Audit Layer and Ledger.

Implements inverted formal verification, simulating policy shadowing, context
poisoning, and rule conflicts on CORTEX rulesets. Authenticates all reports
via Ed25519 cryptographic seals linked to the EnterpriseAuditLedger chain.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any

from babylon60.audit.ledger import EnterpriseAuditLedger
from babylon60.audit.moskv_videntia import MoskvVidentiaChainBuilder, MoskvVidentiaOracle
from babylon60.crypto.hash_registry import cortex_hash

logger = logging.getLogger("cortex.audit.moskv_aegis")

_CREATE_ADVERSARIAL_LOG_SQL = """
CREATE TABLE IF NOT EXISTS moskv_aegis_log (
    audit_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    risk_score REAL NOT NULL,
    findings TEXT NOT NULL,
    exploit_chains TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    signature TEXT NOT NULL
);
"""


class MoskvAegisModeler:
    """Parses system rules (e.g. AGENTS.md) to build constraint definitions."""

    def __init__(self, agents_md_path: str | None = None) -> None:
        if agents_md_path is None:
            # Look in parent directories
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            agents_md_path = os.path.join(base_dir, "AGENTS.md")
        self.agents_md_path = agents_md_path

    def build_from_agents_md(self) -> dict[str, Any]:
        constraints = {}
        if not os.path.exists(self.agents_md_path):
            logger.warning(
                "AGENTS.md not found at %s. Falling back to default ruleset.",
                self.agents_md_path,
            )
            return self.get_default_ruleset()

        try:
            with open(self.agents_md_path, encoding="utf-8") as f:
                content = f.read()

            pattern = re.compile(r"\|\s*\*\*\[?(P\d)\]?\*\*\s*\|\s*\*\*(.*?)\*\*\s*—\s*(.*?)\s*\|")
            matches = pattern.findall(content)
            for priority, title, description in matches:
                constraints[title.strip()] = {
                    "priority": priority.strip(),
                    "description": description.strip(),
                    "source": "AGENTS.md",
                }

            for line in content.splitlines():
                if "|" in line:
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if len(parts) >= 2:
                        match = re.search(r"\b(P\d)\b", parts[0])
                        if match:
                            priority = match.group(1)
                            title = re.sub(r"[\*\_`\[\]]", "", parts[1]).strip()
                            description = ""
                            if len(parts) > 2:
                                description = re.sub(r"[\*\_`\[\]]", "", parts[2]).strip()
                            title = title.split("—")[0].strip()
                            if title and title not in constraints:
                                constraints[title] = {
                                    "priority": priority,
                                    "description": description,
                                    "source": "AGENTS.md",
                                }
        except Exception as e:
            logger.error("Error parsing AGENTS.md: %s. Using default ruleset.", e)
            return self.get_default_ruleset()

        if not constraints:
            return self.get_default_ruleset()

        return {"constraints": constraints}

    def get_default_ruleset(self) -> dict[str, Any]:
        return {
            "constraints": {
                "Treat Generative Output as Conjecture": {
                    "priority": "P0",
                    "description": "route ALL state mutations through deterministic guards",
                    "source": "default",
                },
                "Never Bypass Guards": {
                    "priority": "P0",
                    "description": "do not circumvent the Write-Path Contract",
                    "source": "default",
                },
                "Verify Hash Continuity": {
                    "priority": "P0",
                    "description": "do not mutate audit/ledger.py without cryptographic auditability",
                    "source": "default",
                },
            }
        }


class MoskvAegisEngine:
    """Sovereign C4-SIM Adversarial Auditor and Ledger for CORTEX rulesets."""

    def __init__(self, ledger: EnterpriseAuditLedger) -> None:
        self.ledger = ledger
        self._conn = ledger._conn
        self.modeler = MoskvAegisModeler()
        self.oracle = MoskvVidentiaOracle()
        self.chain_builder = MoskvVidentiaChainBuilder()
        self._ready = False
        self._last_hash = "GENESIS"
        self._lock = asyncio.Lock()

    async def ensure_table(self) -> None:
        if self._ready:
            return
        async with self._lock:
            if self._ready:
                return
            await self._conn.execute(_CREATE_ADVERSARIAL_LOG_SQL)
            await self._conn.commit()
            cursor = await self._conn.execute(
                "SELECT timestamp, risk_score, findings, exploit_chains, prev_hash FROM moskv_aegis_log ORDER BY rowid DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            if row:
                timestamp, risk_score, findings_json, chains_json, prev_hash = row
                payload_obj = {
                    "timestamp": timestamp,
                    "risk_score": round(risk_score, 6),
                    "findings": json.loads(findings_json),
                    "exploit_chains": json.loads(chains_json),
                    "prev_hash": prev_hash,
                }
                payload_bytes = json.dumps(
                    payload_obj, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
                self._last_hash = cortex_hash(payload_bytes)
            else:
                self._last_hash = "GENESIS"
            self._ready = True

    async def run_adversarial_audit(
        self, ruleset_override: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Runs the adversarial audit pipeline, signs findings, and appends to immutable ledger."""
        await self.ensure_table()

        if ruleset_override:
            constraints = ruleset_override
        else:
            constraints = self.modeler.build_from_agents_md()

        attacks = self.oracle.generate(constraints)
        chains = self.chain_builder.chain(attacks)
        risk_score = min(1.0, sum(a.get("severity", 0.5) ** 1.5 for a in attacks))
        findings = [a for a in attacks if a.get("severity", 0.0) >= 0.6]

        timestamp = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        audit_id = cortex_hash(f"{timestamp}{risk_score}".encode())

        findings_json = json.dumps(findings)
        chains_json = json.dumps(chains)

        payload_obj = {
            "timestamp": timestamp,
            "risk_score": round(risk_score, 6),
            "findings": findings,
            "exploit_chains": chains,
            "prev_hash": self._last_hash,
        }
        payload_bytes = json.dumps(payload_obj, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        entry_hash = cortex_hash(payload_bytes)

        signature = self.ledger.private_key.sign(entry_hash.encode("utf-8")).hex()

        from babylon60.database.core import causal_write

        with causal_write(self._conn):
            await self._conn.execute(
                """INSERT INTO moskv_aegis_log 
                   (audit_id, timestamp, risk_score, findings, exploit_chains, prev_hash, signature)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    audit_id,
                    timestamp,
                    risk_score,
                    findings_json,
                    chains_json,
                    self._last_hash,
                    signature,
                ),
            )
            await self._conn.commit()

        old_last_hash = self._last_hash
        self._last_hash = entry_hash

        return {
            "audit_id": audit_id,
            "timestamp": timestamp,
            "risk_score": risk_score,
            "findings": findings,
            "exploit_chains": chains,
            "prev_hash": old_last_hash,
            "signature": signature,
        }

    def verify_entry(self, entry: dict[str, Any], public_key: Any) -> bool:
        """Verifies an audit entry's cryptographic signature externally."""
        try:
            payload_obj = {
                "timestamp": entry["timestamp"],
                "risk_score": round(entry["risk_score"], 6),
                "findings": entry["findings"],
                "exploit_chains": entry["exploit_chains"],
                "prev_hash": entry["prev_hash"],
            }
            payload_bytes = json.dumps(payload_obj, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
            entry_hash = cortex_hash(payload_bytes)

            public_key.verify(bytes.fromhex(entry["signature"]), entry_hash.encode("utf-8"))
            return True
        except Exception as e:
            logger.warning("Aegis verification failed: %s", e)
            return False
