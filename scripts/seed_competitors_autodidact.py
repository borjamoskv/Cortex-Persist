"""AUTODIDACT-Ω: Automated Crystal Persistence — Competitor Reverse Engineering

Seeds the reverse-engineered competitive analysis into CORTEX's memory ledger.
Focuses on the three axes: Memory Infrastructure, EU AI Act Compliance, and Trust/Audit.
"""

import asyncio
import os
import subprocess
import sys

PROJECT_ROOT = "/Users/borjafernandezangulo/30_CORTEX"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ═══ Crystal Definitions ═══

CRYSTALS: list[dict] = [
    {
        "project": "cortex",
        "content": (
            "Vanta, OneTrust, and ComplyACT provide EU AI Act compliance but operate strictly as "
            "documental/paper compliance platforms outside the AI runtime. They do not extract "
            "immutable evidence from the agent's reasoning or execution graph."
        ),
        "fact_type": "knowledge",
        "tags": ["competitors", "eu-ai-act", "vanta", "onetrust", "compliance"],
        "confidence": "C5",
        "source": "autodidact-omega:competitive-analysis-2026",
    },
    {
        "project": "cortex",
        "content": (
            "CORTEX possesses an asymmetric advantage in EU AI Act compliance (Article 12): "
            "it generates compliance cryptographically from within the AI via `ledger.py`, "
            "rather than relying on human-filled checklists like Vanta or OneTrust."
        ),
        "fact_type": "knowledge",
        "tags": ["cortex", "eu-ai-act", "article-12", "ledger", "asymmetric-advantage"],
        "confidence": "C5",
        "source": "autodidact-omega:structural-synthesis",
    },
    {
        "project": "cortex",
        "content": (
            "Mem0 provides a dual-store memory layer (Vector + Knowledge Graph) for LLMs, "
            "but it implements 'memory without trust'. It lacks a cryptographic hash-chain "
            "to audit memory manipulations (ADD/UPDATE/DELETE)."
        ),
        "fact_type": "knowledge",
        "tags": ["competitors", "memory", "mem0"],
        "confidence": "C5",
        "source": "autodidact-omega:competitive-analysis-2026",
    },
    {
        "project": "cortex",
        "content": (
            "Letta (ex-MemGPT) implements an LLM-as-OS architecture with virtual context management "
            "and self-editing memory. Weakness vs CORTEX: No deterministic validation. The agent edits "
            "its memory without cryptographic constraints."
        ),
        "fact_type": "knowledge",
        "tags": ["competitors", "memory", "letta", "memgpt"],
        "confidence": "C5",
        "source": "autodidact-omega:competitive-analysis-2026",
    },
    {
        "project": "cortex",
        "content": (
            "Zep AI utilizes a Temporal Knowledge Graph (Graphiti) with a bi-temporal model "
            "(Event Time + Ingestion Time). Weakness vs CORTEX: Heavy cloud/microservice "
            "dependency; lacks local-first sovereignty."
        ),
        "fact_type": "knowledge",
        "tags": ["competitors", "memory", "zep-ai", "graphiti"],
        "confidence": "C4",
        "source": "autodidact-omega:competitive-analysis-2026",
    },
    {
        "project": "cortex",
        "content": (
            "No current competitor successfully overlaps the three critical infrastructure quadrants: "
            "1. Epistemic Memory (like Mem0/Letta), 2. EU AI Act Compliance (like Vanta/OneTrust), "
            "3. Trust/Cryptographic Audit (like LangSmith/W&B). CORTEX is the sole occupant of this intersection."
        ),
        "fact_type": "bridge",
        "tags": ["cortex", "strategy", "market-gap", "competitors"],
        "confidence": "C4",
        "source": "autodidact-omega:competitive-analysis-2026",
    },
    {
        "project": "cortex",
        "content": (
            "The greatest structural threat to CORTEX in 2026 is a merger or profound partnership "
            "between a memory framework (e.g., Letta) and a compliance suite (e.g., Vanta). However, "
            "retrofitting cryptographic tensor isolation post-hoc is an architectural anti-pattern."
        ),
        "fact_type": "issue",
        "tags": ["cortex", "threat-model", "competitors", "2026"],
        "confidence": "C3",
        "source": "autodidact-omega:strategic-synthesis",
    },
]


async def main():
    print(f"🎓 AUTODIDACT-Ω [COMPETITORS]: Seeding {len(CRYSTALS)} crystals via CLI...")

    ids = []
    # Usar el sistema directamente ya que estamos corriendo esto desde un entorno local
    cortex_bin = "cortex"
    cli_base = [cortex_bin, "memory", "store"]

    for i, crystal in enumerate(CRYSTALS):
        tags = ",".join(crystal.get("tags", []))
        cmd = [
            *cli_base,
            "--type",
            crystal["fact_type"],
            "--confidence",
            crystal["confidence"],
            "--source",
            crystal["source"],
        ]
        if tags:
            cmd.extend(["--tags", tags])
        # Positional args: PROJECT CONTENT
        cmd.append(crystal["project"])
        cmd.append(crystal["content"])

        try:
            env = os.environ.copy()
            env["TOKENIZERS_PARALLELISM"] = "false"

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                env=env,
            )
            label = crystal["fact_type"].upper()
            if result.returncode == 0:
                ids.append(i)
                print(f"  ✅ [{label}] {crystal['content'][:55]}...")
            else:
                err = result.stderr.strip().split("\n")[-1] if result.stderr else "?"
                print(f"  ❌ [{label}] {err}")
        except FileNotFoundError:
            print(
                f"  ⚠️ CORTEX CLI no encontrado. Omitiendo persistencia de: {crystal['content'][:30]}..."
            )
            break  # Abort if cortex CLI is not in path

    print("\n" + "═" * 60)
    print("  ∴  AUTODIDACT-Ω Crystal Persistence Complete")
    print(f"  ◈  Crystals: {len(ids)}/{len(CRYSTALS)} persisted")
    print("═" * 60)


if __name__ == "__main__":
    asyncio.run(main())
