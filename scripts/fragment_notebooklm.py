#!/usr/bin/env python3
"""
CORTEX → NotebookLM Domain Fragmenter v1.0

Splits the CORTEX knowledge export into semantic domain fragments,
each optimized for NotebookLM's 500K word/source limit.

Domain taxonomy:
  - cortex-core:        CORTEX engine, CLI, API, schema, migrations
  - cortex-infra:       Deployment, MCP, daemons, security, system
  - cortex-agents:      Swarm, consensus, agents, bridges
  - cortex-products:    Naroa, NotchLive, Moltbook, NFT, Sonic, etc.
  - cortex-operations:  Ghost-control, autorouter, SAP, mailtv
  - cortex-strategy:    Commerce, pricing, marketing, ROI, monetization
  - cortex-research:    Evolution, Ouroboros, temporal, singularity

Usage:
    python3 scripts/fragment_notebooklm.py
    python3 scripts/fragment_notebooklm.py --output-dir notebooklm_domains
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Ninja Bypass for pysqlite3
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import pandas as pd

CORTEX_DB_PATH = Path.home() / ".cortex" / "cortex.db"
DEFAULT_OUTPUT_DIR = Path("notebooklm_domains")

# ── Domain Taxonomy ──────────────────────────────────────────────────
# Maps project names (case-insensitive) to domain fragments.
# Projects not explicitly mapped go to "misc".

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

# Build reverse lookup: project → domain
_PROJECT_TO_DOMAIN: dict[str, str] = {}
for domain, projects in DOMAIN_MAP.items():
    for proj in projects:
        _PROJECT_TO_DOMAIN[proj] = domain


def classify_project(project: str) -> str:
    """Classify a project into a domain fragment."""
    return _PROJECT_TO_DOMAIN.get(project, "cortex-misc")


DOMAIN_DESCRIPTIONS: dict[str, str] = {
    "cortex-core": (
        "Motor central de CORTEX: engine, CLI, API, schema, migrations, "
        "LLM router, exports, y todas las versiones (V7/V8/Persist)."
    ),
    "cortex-infra": (
        "Infraestructura y deployment: sistema operativo, daemons, "
        "seguridad, DNS, testing, y configuración."
    ),
    "cortex-agents": (
        "Inteligencia de enjambre: agentes, swarm, consenso, bridges "
        "cross-project, Kimi, Centauro, y protocolos multi-agente."
    ),
    "cortex-products": (
        "Productos y proyectos: Naroa, NotchLive, Moltbook, Sonic, "
        "NFT collections, webs, y aplicaciones."
    ),
    "cortex-operations": (
        "Operaciones: ghost-control, autorouter, SAP, correo, "
        "ecosistema, reporting, scraping, y traducciones."
    ),
    "cortex-strategy": (
        "Estrategia y comercialización: pricing, commerce, landing pages, "
        "ROI, monetización, y bots de venta."
    ),
    "cortex-research": (
        "Investigación y evolución: Ouroboros, temporal, singularity, "
        "Apotheosis, evolución, meta-cognición, y axiomas."
    ),
    "cortex-misc": ("Proyectos no clasificados o emergentes."),
}


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    """Generate domain-fragmented NotebookLM sources."""
    output_dir.mkdir(exist_ok=True)

    conn = sqlite3.connect(str(CORTEX_DB_PATH))
    df = pd.read_sql_query(
        "SELECT id, project, fact_type, content, confidence, tags "
        "FROM facts WHERE valid_until IS NULL",
        conn,
    )
    conn.close()

    # Classify
    df["domain"] = df["project"].apply(classify_project)
    ts = datetime.now().strftime("%Y-%m-%d")

    stats: list[dict] = []

    for domain in sorted(df["domain"].unique()):
        domain_df = df[df["domain"] == domain]
        projects_in_domain = sorted(domain_df["project"].unique())
        filename = output_dir / f"{domain}-{ts}.md"
        desc = DOMAIN_DESCRIPTIONS.get(domain, "")

        lines: list[str] = []
        lines.append(f"# 🧠 CORTEX — {domain.upper()}\n\n")
        lines.append(
            f"> Snapshot: {ts} | Facts: {len(domain_df)} | Proyectos: {len(projects_in_domain)}\n\n"
        )
        if desc:
            lines.append(f"**Dominio:** {desc}\n\n")
        lines.append("---\n\n")

        for proj in projects_in_domain:
            proj_df = domain_df[domain_df["project"] == proj]
            lines.append(f"## {proj}\n")
            lines.append(f"*{len(proj_df)} hechos*\n\n")

            for ftype in sorted(proj_df["fact_type"].unique()):
                lines.append(f"### {ftype.capitalize()}\n")
                type_df = proj_df[proj_df["fact_type"] == ftype]
                for _, row in type_df.iterrows():
                    short_id = str(row.get("id"))[:8] if "id" in row and row["id"] else "00000000"
                    shadow_open = f"∆_CTX:{short_id.upper()}"
                    shadow_close = f"∇_CTX:{short_id.upper()}"

                    clean_content = str(row["content"]).replace("\n", " ")
                    line = f"`[{shadow_open}]` {clean_content}"

                    conf = row.get("confidence", "stated")
                    tags_raw = row.get("tags", "[]")

                    meta = []
                    if conf and conf != "stated":
                        meta.append(f"conf:{conf}")
                    if tags_raw and tags_raw != "[]":
                        try:
                            tag_list = (
                                json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw
                            )
                            if tag_list:
                                meta.append(f"tax:{','.join(tag_list)}")
                        except (ValueError, TypeError):
                            pass

                    if meta:
                        line += f" `{' | '.join(meta)}`"

                    line += f" `[{shadow_close}]`"
                    lines.append(f"> {line}\n\n")
            lines.append("---\n\n")

        content = "".join(lines)
        word_count = len(content.split())
        char_count = len(content)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        status = "✅" if word_count < 500_000 else "⚠️ OVER LIMIT"
        stats.append(
            {
                "domain": domain,
                "projects": len(projects_in_domain),
                "facts": len(domain_df),
                "words": word_count,
                "chars": char_count,
                "status": status,
                "file": filename.name,
            }
        )
        print(
            f"{status} {filename.name}: {len(domain_df)} facts, "
            f"{word_count:,} words, {len(projects_in_domain)} projects"
        )

    # Summary
    print(f"\n{'─' * 60}")
    print("📊 Domain Fragmentation Summary")
    print(f"{'─' * 60}")
    total_facts = sum(s["facts"] for s in stats)
    total_words = sum(s["words"] for s in stats)
    for s in stats:
        pct = (s["facts"] / total_facts * 100) if total_facts else 0
        print(
            f"  {s['domain']:25s} │ {s['facts']:5d} facts ({pct:4.1f}%) │ "
            f"{s['words']:7,} words │ {s['projects']:3d} projs"
        )
    print(f"{'─' * 60}")
    print(
        f"  {'TOTAL':25s} │ {total_facts:5d} facts         │ "
        f"{total_words:7,} words │ {len(stats):3d} domains"
    )
    print("\n💡 Cada archivo < 500K words → safe para NotebookLM individual source")
    print(f"📁 Output: {output_dir}/")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fragment CORTEX for NotebookLM domains")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: notebooklm_domains)",
    )
    args = parser.parse_args()
    run(args.output_dir)
