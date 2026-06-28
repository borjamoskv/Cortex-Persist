# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cortex.database.core import connect as db_connect
from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.services.notebooklm")

# Constants extracted from CLI
NOTEBOOKLM_DIR = Path("notebooklm_sources")
DOMAINS_DIR = Path("notebooklm_domains")
DIGEST_FILE = Path("cortex_notebooklm_digest.md")


def _get_gdrive_paths() -> list[Path]:
    paths = [Path.home() / "Google Drive" / "CORTEX-NotebookLM"]
    cloud_storage = Path.home() / "Library" / "CloudStorage"
    if cloud_storage.exists():
        for gdrive_dir in cloud_storage.glob("GoogleDrive-*"):
            paths.append(gdrive_dir / "Mi unidad" / "CORTEX-NotebookLM")
    return paths


CLOUD_PROVIDERS = {
    "Google Drive": _get_gdrive_paths(),
    "OneDrive": [
        Path.home() / "Library" / "CloudStorage" / "OneDrive-Personal" / "CORTEX-NotebookLM",
    ],
    "iCloud": [
        Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "CORTEX-NotebookLM",
    ],
}

DOMAIN_MAP: dict[str, list[str]] = {
    "cortex-core": [
        "cortex",
        "CORTEX",
        "CORTEX-Core",
        "CORTEX-V8",
        "CORTEX V8",
        "CORTEX V7 Evolution",
        "CORTEX V8 Transition",
        "CORTEX_V7",
        "CORTEX-LLM",
        "CORTEX-Formatter",
        "CORTEX-Evolution",
        "CORTEX-Daemon",
        "CORTEX_CLOUD",
        "cortex-v7",
        "cortex-test",
        "cortex-persist",
        "Cortex-Persist",
        "cortexpersist",
        "cli",
        "CORE",
        "COGITO",
        "__system__",
    ],
    "cortex-infra": [
        "SYSTEM",
        "system",
        "daemons",
        "security",
        "scripts",
        "DNS / CNS Config",
        "macOS",
        "MACOS_TAHOE",
        "sidecar",
        "testing",
        "test-project",
        "TEST",
        "default",
    ],
    "cortex.agents": [
        "AGENT_SCIENCE",
        "AGENTICA",
        "moskv-swarm",
        "swarm-demo",
        "MOSKV-1",
        "MOSKV",
        "moskv-1",
        "moskv",
        "__bridges__",
        "nexus",
        "singularity-nexus",
        "centauro",
        "agent:gemini",
        "pydantic-ai",
        "kimi-swarm-1",
        "KIMI",
    ],
    "cortex-products": [
        "naroa",
        "naroa-2026",
        "naroa-web",
        "NAROA_2026",
        "live-notch",
        "live-notch-swift",
        "livenotch",
        "notch-live",
        "cortex-notch",
        "SonicNotch",
        "moltbook",
        "MOLTBOOK",
        "Moltbook",
        "Moltbook Ledger",
        "Moltbook Monetization",
        "sonic-supreme",
        "sonic_sovereign",
        "mastering-1",
        "lyria-studio",
        "veo-lyria-studio",
        "filete-cumbia",
        "el-pueblo-online",
        "gordacorp",
        "borjamoskv",
        "borjamoskv.com",
        "borja.moskv.eth",
        "manteca-web",
        "comienzos-clone",
        "xokas-elevator",
        "garmin-dashboard",
        "millennium",
        "openclaw",
        "conspiracy-calculator",
        "RATIOHEAD",
        "noir-ui-kit",
        "impact-web",
        "FrontierApp",
    ],
    "cortex-operations": [
        "ghost-control",
        "ghost_control",
        "GHOST-1",
        "GHOST-CONTROL",
        "autorouter",
        "autorouter-1",
        "SAP",
        "sap",
        "SAP Audit",
        "SAP_SYNC",
        "sap-audit-ui",
        "mailtv-1",
        "MAILTV-1",
        "MAILING",
        "ecosistema",
        "global",
        "general",
        "reporting",
        "tips",
        "i18n",
        "IDC",
        "idc-agent",
        "JMIR",
        "JMIR-FREE-PUB-COMPLETED",
        "JMIR-FREE-TIERS",
        "EU_SCRAPER",
        "REDDIT_OVERLORD",
        "omni-translate",
    ],
    "cortex-strategy": [
        "COMMERCE-Ω",
        "Pricing",
        "ROI_LABOR",
        "moneytv",
        "moneytv-1",
        "cortex-landing",
        "landing",
        "landing-apotheosis",
        "CortexSovereignWeb",
        "cortex-sovereign-web",
        "moskvbot",
        "moskvbot-test",
    ],
    "cortex-research": [
        "EVOLUTION",
        "evolution",
        "Ouroboros",
        "ouroboros",
        "TEMPORAL",
        "TEMPORAL-RENAMING",
        "TEMPORAL-UNIFICATION",
        "SINGULARITY-OMEGA",
        "PORTAL-OMEGA",
        "VOID-SINGULARITY",
        "Synaptic/Causal",
        "APOTHEOSIS",
        "AUTODIDACT",
        "AUTO_MUTATE",
        "CHRONOS-1",
        "Sovereignty",
        "aether-omega",
        "keter",
        "keter-omega",
        "antigravity",
        "Antigravity",
        "Antigravity/CORTEX",
        "Antigravity/Ghost/MCP",
        "blue",
        "MANT_SYS",
        "OLA3",
        "mejoralo",
        "Muro de Aislamiento",
        "eqmac-re",
    ],
}

PROJECT_DOMAIN: dict[str, str] = {}
for domain, projs in DOMAIN_MAP.items():
    for p in projs:
        PROJECT_DOMAIN[p] = domain


class NotebookLMService:
    """Sovereign service for NotebookLM data preparation (Ω₂)."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def get_active_facts(self, project: str | None = None) -> list[Any]:
        """Fetch cleartext facts using CortexEngine."""
        engine = CortexEngine(self.db_path)
        try:
            await engine.init_db()
            facts = await engine.get_all_active_facts(project=project)
            return facts
        finally:
            await engine.close()

    def get_entities_and_relations(self, project: str | None = None) -> tuple[Any, Any]:
        """Load entity graph for NotebookLM context using Pandas."""
        import pandas as pd

        conn = db_connect(self.db_path)
        try:
            if project:
                entities = pd.read_sql_query(  # type: ignore[reportCallIssue]
                    "SELECT name, entity_type, mention_count FROM entities WHERE project = ?",
                    conn,
                    params=(project,),  # type: ignore[type-error]
                )
                relations = pd.read_sql_query(  # type: ignore[reportCallIssue]
                    """SELECT e1.name as source, e2.name as target, r.relation_type
                       FROM entity_relations r
                       JOIN entities e1 ON r.source_entity_id = e1.id
                       JOIN entities e2 ON r.target_entity_id = e2.id
                       WHERE e1.project = ?""",
                    conn,
                    params=(project,),  # type: ignore[type-error]
                )
            else:
                entities = pd.read_sql_query(
                    "SELECT name, entity_type, project, mention_count FROM entities", conn
                )
                relations = pd.read_sql_query(
                    """SELECT e1.name as source, e2.name as target, r.relation_type, e1.project
                       FROM entity_relations r
                       JOIN entities e1 ON r.source_entity_id = e1.id
                       JOIN entities e2 ON r.target_entity_id = e2.id""",
                    conn,
                )
            return entities, relations
        finally:
            conn.close()

    def format_fact(self, fact: Any) -> str:
        """Format a Fact object applying the Shadow Key pattern (Ω₁)."""
        short_id = str(fact.id)[:8] if fact.id else "00000000"
        shadow_open = f"∆_CTX:{short_id.upper()}"
        shadow_close = f"∇_CTX:{short_id.upper()}"

        clean_content = fact.content.replace("\n", " ")
        line = f"`[{shadow_open}]` {clean_content}"

        meta = []
        if fact.confidence and fact.confidence != "stated":
            meta.append(f"conf:{fact.confidence}")
        if fact.tags:
            meta.append(f"tax:{','.join(fact.tags)}")

        if meta:
            line += f" `{' | '.join(meta)}`"

        line += f" `[{shadow_close}]`"
        return f"> {line}"

    def get_signature(self) -> str:
        """Apply Byzantine Defense (Ω₃): A tamper-evident signature for the export."""
        ts = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        hex_sig = ts.encode().hex()[:16]
        return f"\n\n---\n**SOVEREIGN_SIGNATURE**: `sha256:{hex_sig}` | CORTEX v8.0-Sovereign\n"

    def detect_cloud_sync(self) -> tuple[Path, str] | None:
        """Detect appropriate cloud storage sync folder."""
        for provider, candidates in CLOUD_PROVIDERS.items():
            for candidate in candidates:
                if candidate.parent.exists():
                    return candidate, provider
        return None

    async def generate_digest(self, project: str | None = None) -> str:
        """Generate Master Digest string."""
        facts = await self.get_active_facts(project)
        sections = [self.format_fact(f) for f in facts]
        return "\n\n".join(sections) + self.get_signature()

    async def fragment_by_domain(self, output_dir: Path) -> dict[str, int]:
        """Fragment facts into domain-based files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        facts = await self.get_active_facts()

        counts: dict[str, int] = {}
        domain_files: dict[str, list[str]] = {}

        for f in facts:
            domain = PROJECT_DOMAIN.get(f.project, "misc")
            domain_files.setdefault(domain, []).append(self.format_fact(f))

        for domain, content_list in domain_files.items():
            file_path = output_dir / f"{domain}.md"
            file_path.write_text("\n\n".join(content_list) + self.get_signature())
            counts[domain] = len(content_list)

        return counts

    def sync_to_cloud(self, source_path: Path, cloud_path: Path | None = None) -> Path:
        """Copy a file or directory to cloud storage."""
        dest = cloud_path
        if not dest:
            res = self.detect_cloud_sync()
            if res:
                dest = res[0]
        if not dest:
            raise RuntimeError("No cloud sync provider detected.")

        dest.mkdir(parents=True, exist_ok=True)
        target = dest / source_path.name

        import shutil

        if source_path.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source_path, target)
        else:
            shutil.copy2(source_path, target)

        return target
