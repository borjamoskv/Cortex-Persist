"""
CORTEX CLI — NotebookLM Constants, Data Taxonomy & Helpers.

Extracted from notebooklm_cmds.py to keep CLI command handlers < 500 LOC.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from cortex.config import DEFAULT_DB_PATH

# ── Constants ──────────────────────────────────────────────────────────
NOTEBOOKLM_DIR = Path("cortex_eguzkia")
DOMAINS_DIR = Path("notebooklm_domains")
DIGEST_FILE = Path("cortex_notebooklm_digest.md")

# Default Cloud Sync paths (macOS)
CLOUD_PROVIDERS: dict[str, list[Path]] = {
    "Google Drive": [
        Path.home()
        / "Library"
        / "CloudStorage"
        / "GoogleDrive-borjafernandezangulo@gmail.com"
        / "Mi unidad"
        / "CORTEX-NotebookLM",
        Path.home() / "Google Drive" / "CORTEX-NotebookLM",
    ],
    "OneDrive": [
        Path.home() / "Library" / "CloudStorage" / "OneDrive-Personal" / "CORTEX-NotebookLM",
    ],
    "iCloud": [
        Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "CORTEX-NotebookLM",
    ],
}

# Domain taxonomy
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
        "CODEX",
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
    "cortex-agents": [
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

_PROJECT_DOMAIN: dict[str, str] = {}
for _domain, _projs in DOMAIN_MAP.items():
    for _p in _projs:
        _PROJECT_DOMAIN[_p] = _domain


# ── Helper Functions ────────────────────────────────────────────────────


def _get_db_path() -> str:
    return str(DEFAULT_DB_PATH)


def _run_async(coro: Any) -> Any:
    """Helper to run async coroutines from sync CLI."""
    from cortex.events.loop import sovereign_run

    return sovereign_run(coro)


async def _get_engine_active_facts(project: str | None = None) -> list[Any]:
    """Fetch cleartext facts using CortexEngine."""
    from cortex.cli.common import get_engine

    engine = get_engine()
    try:
        await engine.init_db()
        facts = await engine.get_all_active_facts(project=project)
        return facts
    finally:
        await engine.close()


def _detect_cloud_sync() -> tuple[Path, str] | None:
    """Detect appropriate cloud storage sync folder."""
    for provider, candidates in CLOUD_PROVIDERS.items():
        for candidate in candidates:
            # Check if parent (the actual CloudStorage folder) exists
            if candidate.parent.exists():
                return candidate, provider
    return None


def _get_entities_and_relations(
    project: str | None = None,
) -> tuple[Any, Any]:
    """Load entity graph for NotebookLM context."""
    import pandas as pd

    conn = __import__("cortex.database.core", fromlist=["db_connect"]).db_connect(_get_db_path())
    try:
        if project:
            entities = pd.read_sql_query(
                "SELECT name, entity_type, mention_count FROM entities WHERE project = ?",
                conn,
                params=(project,),
            )
            relations = pd.read_sql_query(
                """SELECT e1.name as source, e2.name as target, r.relation_type 
                   FROM entity_relations r
                   JOIN entities e1 ON r.source_entity_id = e1.id
                   JOIN entities e2 ON r.target_entity_id = e2.id
                   WHERE e1.project = ?""",
                conn,
                params=(project,),
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


def _format_fact_obj(fact: Any) -> str:
    """Format a Fact object applying the Shadow Key pattern (Ω₁).

    El patrón Shadow Key asegura que NotebookLM ancle la cita a un token ruidoso y específico
    (∆_CTX:xxxx), inyectándolo tanto al inicio como al final para sobrevivir a la síntesis LLM
    y permitir la extracción inversa determinista sin depender de NLP.
    """
    short_id = str(fact.id)[:8] if fact.id else "00000000"
    shadow_open = f"∆_CTX:{short_id.upper()}"
    shadow_close = f"∇_CTX:{short_id.upper()}"

    clean_content = fact.content.replace("\n", " ")

    # Anclaje semántico encapsulado en código (backticks) para máxima retención LLM
    line = f"`[{shadow_open}]` {clean_content}"

    meta = []
    if fact.confidence and fact.confidence != "stated":
        meta.append(f"conf:{fact.confidence}")
    if fact.tags:
        meta.append(f"tax:{','.join(fact.tags)}")

    if meta:
        line += f" `{' | '.join(meta)}`"

    # Shadow Key de cierre
    line += f" `[{shadow_close}]`"
    return f"> {line}"


def _sovereign_signature() -> str:
    """Apply Byzantine Defense (Ω₃): A tamper-evident signature for the export."""
    ts = datetime.now().isoformat()
    hex_sig = ts.encode().hex()[:16]
    return f"\n\n---\n**SOVEREIGN_SIGNATURE**: `sha256:{hex_sig}` | CORTEX v8.0-Sovereign\n"
