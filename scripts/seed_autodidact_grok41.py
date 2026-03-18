"""AUTODIDACT-Ω: Automated Crystal Persistence — xAI Grok 4.1

Seeds 12 falsifiable axioms extracted from official sources into CORTEX.
Pipeline: SOURCE_ACQUIRE → CHUNK → EPISTEMIC_FILTER → CAUSAL_COMPRESS → DEDUP → CRYSTAL_PERSIST
"""

import asyncio
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv()

# ═══ Crystal Definitions ═══

CRYSTALS: list[dict] = [
    {
        "project": "cortex",
        "content": (
            "Grok 4 uses RL at pretraining scale on 200K GPUs (Colossus). "
            "Not fine-tuning — reinforcement learning as primary training phase, "
            "expanded beyond math/code to many domains. "
            "Grok 4 is always a reasoning model: no non-reasoning mode exists."
        ),
        "fact_type": "knowledge",
        "tags": ["xai", "grok-4", "architecture", "reinforcement-learning"],
        "confidence": "C5",
        "source": "autodidact-omega:x.ai/news/grok-4",
        "meta": {
            "crystal_type": "axiom",
            "source_type": "web",
            "domain": "llm-architecture",
            "temporal_marker": "2025-07-09",
        },
    },
    {
        "project": "cortex",
        "content": (
            "Grok 4.1 has two operational modes: 'tensor' (fast-response, low latency) "
            "and 'quasarflux' (multi-step thinking with reasoning tokens). "
            "Auto mode switches between them. No other frontier model offers "
            "automatic switching between latency and depth."
        ),
        "fact_type": "knowledge",
        "tags": ["xai", "grok-4.1", "dual-mode", "tensor", "quasarflux"],
        "confidence": "C4",
        "source": "autodidact-omega:betterstack.com+venturebeat.com",
        "meta": {
            "crystal_type": "axiom",
            "source_type": "web",
            "domain": "llm-architecture",
            "temporal_marker": "2025-11",
        },
    },
    {
        "project": "cortex",
        "content": (
            "Context windows (March 2026): "
            "grok-4.1-fast = 2M tokens, grok-4.1 main = 256K tokens, "
            "grok-4.20-beta = 2M tokens. "
            "Source: docs.x.ai/docs/models."
        ),
        "fact_type": "knowledge",
        "tags": ["xai", "grok-4.1", "context-window", "specs"],
        "confidence": "C5",
        "source": "autodidact-omega:docs.x.ai/docs/models",
        "meta": {
            "crystal_type": "axiom",
            "source_type": "web",
            "domain": "llm-specs",
            "temporal_marker": "2026-03-18",
        },
    },
    {
        "project": "cortex",
        "content": (
            "Grok 4.1 reduced hallucination rate from 12.09% to 4.22% "
            "in non-reasoning mode. Grok 4.20 Beta further reduces to 4.2%."
        ),
        "fact_type": "knowledge",
        "tags": ["xai", "grok-4.1", "hallucination", "safety"],
        "confidence": "C4",
        "source": "autodidact-omega:betterstack.com",
        "meta": {
            "crystal_type": "discovery",
            "source_type": "web",
            "domain": "llm-safety",
            "temporal_marker": "2025-11",
        },
    },
    {
        "project": "cortex",
        "content": (
            "Grok 4.1 API server-side tools (native, autonomous invocation): "
            "web_search ($5/1K), x_search ($5/1K), code_execution ($5/1K), "
            "view_image (token-based), view_x_video (token-based), "
            "Remote MCP (token-based). "
            "GPT-5.4, Claude 4.6, and Gemini 3.1 Pro do not offer x_search or "
            "native Remote MCP in their APIs. This is the only structurally "
            "irreproducible advantage."
        ),
        "fact_type": "knowledge",
        "tags": ["xai", "grok-4.1", "real-time", "tools", "mcp", "x-search"],
        "confidence": "C5",
        "source": "autodidact-omega:docs.x.ai/docs/models",
        "meta": {
            "crystal_type": "discovery",
            "source_type": "web",
            "domain": "llm-tools",
            "temporal_marker": "2026-03-18",
            "key_differentiator": True,
        },
    },
    {
        "project": "cortex",
        "content": (
            "Grok 4.1 Fast benchmarks (March 2026): "
            "LMSYS Arena #1 (1483 Elo thinking), GPQA Diamond 85.3%, "
            "MMLU Pro 85.4%, MATH 500 99%, AIME 2025 94.3%, "
            "LiveCodeBench 82.2%, HLE 17.6% (fast) / 50.7% (Grok 4 Heavy), "
            "ARC-AGI V2 15.9% (SOTA, 2x Opus 8.6%). "
            "SWE-bench: behind Claude Code and Codex (Musk acknowledged)."
        ),
        "fact_type": "knowledge",
        "tags": ["xai", "grok-4.1", "benchmarks", "march-2026"],
        "confidence": "C4",
        "source": "autodidact-omega:x.ai+designforonline.com",
        "meta": {
            "crystal_type": "discovery",
            "source_type": "web",
            "domain": "llm-benchmarks",
            "temporal_marker": "2026-03-18",
        },
    },
    {
        "project": "cortex",
        "content": (
            "Grok 4.1 Fast pricing: $0.20/M input tokens, $0.50/M output tokens. "
            "Batch API: 50% discount on all token types. "
            "Source: docs.x.ai/docs/models."
        ),
        "fact_type": "knowledge",
        "tags": ["xai", "grok-4.1", "pricing"],
        "confidence": "C5",
        "source": "autodidact-omega:docs.x.ai/docs/models",
        "meta": {
            "crystal_type": "discovery",
            "source_type": "web",
            "domain": "llm-pricing",
            "temporal_marker": "2026-03-18",
        },
    },
    {
        "project": "cortex",
        "content": (
            "Grok 4.1 API supports Remote MCP Tools as server-side tool. "
            "CORTEX can be exposed as MCP server and invoked directly by Grok "
            "during reasoning. No other frontier model offers this capability "
            "natively in the API."
        ),
        "fact_type": "bridge",
        "tags": ["xai", "grok-4.1", "mcp", "cortex", "integration"],
        "confidence": "C4",
        "source": "autodidact-omega:docs.x.ai/docs/models",
        "meta": {
            "crystal_type": "bridge",
            "source_type": "web",
            "domain": "cortex-integration",
            "temporal_marker": "2026-03-18",
            "bridge_endpoints": ["grok-4.1-api", "cortex-mcp-server"],
        },
    },
    {
        "project": "cortex",
        "content": (
            "x_search + web_search as native tools allow Grok to act as "
            "temporal sensor for CORTEX. Pipeline: Grok searches → extracts → "
            "CORTEX validates with guards → persists with confidence C3 "
            "(agent synthesis). Only provider that can feed CORTEX with "
            "temporal signal without external scraper."
        ),
        "fact_type": "bridge",
        "tags": ["xai", "grok-4.1", "cortex", "real-time", "temporal-sensor"],
        "confidence": "C3",
        "source": "autodidact-omega:synthesis",
        "meta": {
            "crystal_type": "bridge",
            "source_type": "agent-synthesis",
            "domain": "cortex-architecture",
            "temporal_marker": "2026-03-18",
            "bridge_endpoints": ["grok-realtime-tools", "cortex-guard-pipeline"],
        },
    },
    {
        "project": "cortex",
        "content": (
            "GHOST: llm_presets.json had context_window=2000000 for xAI default model. "
            "Official docs: grok-4.1 main = 256K, grok-4.1-fast = 2M. "
            "Preset should reflect the default model's window, not Fast variant."
        ),
        "fact_type": "ghost",
        "tags": ["xai", "grok-4.1", "config-ghost", "llm-presets"],
        "confidence": "C5",
        "source": "autodidact-omega:docs.x.ai/docs/models",
        "meta": {
            "crystal_type": "ghost",
            "source_type": "web",
            "domain": "cortex-config",
            "temporal_marker": "2026-03-18",
            "ghost_type": "ux_ghost",
            "remediation": "Update llm_presets.json xai.context_window to 256000",
        },
    },
    {
        "project": "cortex",
        "content": (
            "Musk acknowledged March 2026 that Grok is behind Claude Code and "
            "Codex in coding benchmarks. GPQA: 85.3% vs 91.9% (Claude/Gemini). "
            "Grok's advantage is not raw intelligence — it is real-time tools "
            "+ native MCP + low censorship."
        ),
        "fact_type": "decision",
        "tags": ["xai", "grok-4.1", "weaknesses", "strategic"],
        "confidence": "C4",
        "source": "autodidact-omega:thenextweb.com",
        "meta": {
            "crystal_type": "decision",
            "source_type": "web",
            "domain": "llm-strategy",
            "temporal_marker": "2026-03-18",
        },
    },
    {
        "project": "cortex",
        "content": (
            "Grok 4 Heavy: first model to score 50.7% on Humanity's Last Exam "
            "(text-only subset). Uses parallel test-time compute "
            "(multiple hypotheses simultaneously). ARC-AGI V2: 15.9% "
            "(SOTA, nearly 2x Opus ~8.6%). USAMO 2025: 61.9%."
        ),
        "fact_type": "knowledge",
        "tags": ["xai", "grok-4-heavy", "benchmarks", "frontier"],
        "confidence": "C5",
        "source": "autodidact-omega:x.ai/news/grok-4",
        "meta": {
            "crystal_type": "discovery",
            "source_type": "web",
            "domain": "llm-benchmarks",
            "temporal_marker": "2025-07-09",
        },
    },
]


# Valid fact_types: axiom, bridge, counterfactual, decision, error,
# evolution, ghost, idea, identity, issue, knowledge, preference,
# rule, schema, system_health, test, world-model


async def main():
    import subprocess

    print(f"🎓 AUTODIDACT-Ω: Seeding {len(CRYSTALS)} crystals via CLI...")

    ids = []
    cortex_bin = os.path.join(PROJECT_ROOT, "venv", "bin", "cortex")
    if not os.path.exists(cortex_bin):
        cortex_bin = "cortex"  # fallback to system PATH
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

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        label = crystal["fact_type"].upper()
        if result.returncode == 0:
            ids.append(i)
            print(f"  ✅ [{label}] {crystal['content'][:55]}...")
        else:
            err = result.stderr.strip().split("\n")[-1] if result.stderr else "?"
            print(f"  ❌ [{label}] {err}")

    print("\n" + "═" * 60)
    print("  ∴  AUTODIDACT-Ω Crystal Persistence Complete")
    n_know = sum(1 for c in CRYSTALS if c["fact_type"] == "knowledge")
    n_bridge = sum(1 for c in CRYSTALS if c["fact_type"] == "bridge")
    n_ghost = sum(1 for c in CRYSTALS if c["fact_type"] == "ghost")
    n_decision = sum(1 for c in CRYSTALS if c["fact_type"] == "decision")
    print(f"  ◈  Crystals: {len(ids)}/{len(CRYSTALS)} persisted")
    print(
        f"  ◈  Types: knowledge={n_know}, bridge={n_bridge}, ghost={n_ghost}, decision={n_decision}"
    )
    print("═" * 60)


if __name__ == "__main__":
    asyncio.run(main())
