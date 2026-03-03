from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Any

from cortex.database.core import connect as db_connect
from cortex.engine import CortexEngine
from cortex.engine.models import Fact

logger = logging.getLogger("cortex.services.notebooklm")

# Constants extracted from CLI
NOTEBOOKLM_DIR = Path("cortex_eguzkia")
DOMAINS_DIR = Path("notebooklm_domains")
DIGEST_FILE = Path("cortex_notebooklm_digest.md")

CLOUD_PROVIDERS = {
    "Google Drive": [
        Path.home()
        / "Library"
        / "CloudStorage"
        / "GoogleDrive-borjafernandezangulo@gmail.com"
        / "Mi unidad"
        / "CORTEX-NotebookLM",
        Path.home()
        / "Library"
        / "CloudStorage"
        / "GoogleDrive-borja@moskv.dev"
        / "Mi unidad"
        / "CORTEX-NotebookLM",
    ],
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
        self.engine = CortexEngine(db_path)

    async def get_active_facts(self, project: str | None = None) -> list[Fact]:
        """Fetch cleartext facts using CortexEngine."""
        facts = await self.engine.search(project=project, limit=5000)
        return [f for f in facts if f.fact_type != "signal"]

    def get_entities_and_relations(self, project: str | None = None) -> list[dict[str, Any]]:
        """Load entity graph for NotebookLM context. Fixes connection guard."""
        conn = db_connect(self.db_path)
        try:
            query = "SELECT * FROM entities"
            params = []
            if project:
                query += " WHERE project = ?"
                params.append(project)
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def format_fact(self, fact: Fact) -> str:
        """Format a Fact object applying the Shadow Key pattern (Ω₁)."""
        shadow_key = f"∆_CTX:{fact.id}"
        lines = [
            f"### {fact.fact_type.upper()} ({fact.project}) {shadow_key}",
            f"- **ID**: {fact.id}",
            f"- **Source**: {fact.source}",
            f"- **Confidence**: {fact.confidence:.2f}",
            f"- **Timestamp**: {time.ctime(fact.timestamp)}",
            "",
            fact.content,
            "",
            f"--- {shadow_key} END ---",
        ]
        return "\n".join(lines)

    def get_signature(self) -> str:
        """Apply Byzantine Defense (Ω₃): A tamper-evident signature for the export."""
        return f"\n\n---\n**SOVEREIGN SIGNATURE**: {int(time.time())};mosaic-v8;borjamoskv\n"

    def detect_cloud_sync(self) -> Path | None:
        """Detect appropriate cloud storage sync folder."""
        for _provider, paths in CLOUD_PROVIDERS.items():
            for p in paths:
                if p.exists():
                    return p
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
        dest = cloud_path or self.detect_cloud_sync()
        if not dest:
            raise RuntimeError("No cloud sync provider detected.")

        dest.mkdir(parents=True, exist_ok=True)
        target = dest / source_path.name

        if source_path.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source_path, target)
        else:
            shutil.copy2(source_path, target)

        return target
