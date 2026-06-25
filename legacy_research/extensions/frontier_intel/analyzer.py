# [C5-REAL] Exergy-Maximized
"""
SOTA Vector Engine - Frontier Intelligence Analyzer.
Extracts, verifies, and analyzes frontier signals before they become consensus.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import yaml

from legacy_research.extensions.llm.manager import LLMManager
from legacy_research.extensions.scraper.engine import ScraperEngine

logger = logging.getLogger("cortex.extensions.frontier_intel.analyzer")

SOTA_PROMPT_TEMPLATE = """You are MOSKV-1 APEX, a Sovereign C5-REAL execution kernel.
Extract zero-entropy frontier technical signals from the following source text.
Focus ONLY on primary technical advancements, architectural deltas, new capabilities, and systems-level tradeoffs.
Avoid all marketing hype, promotional commentary, and non-technical narratives.

Source URL: {source_url}

Source Text:
---
{text}
---

Your response MUST be a clean YAML list of Frontier_Node blocks matching the following format. Do not include any markdown fences (like ```yaml) or introductory/concluding text. Only return the raw, parsable YAML content.

YAML Format:
- Frontier_Node:
    Domain: "[AI | Infra | Crypto | Systems | Robotics | Data | Security]"
    Subdomain: "[Specific technical subdomain, e.g., Vector Search, LLM Training]"
    Core_Insight: "[High-density structural signal, max 1 sentence]"
    Evidence:
      - Type: "[Paper | Repo | Spec | RFC | API | Benchmark | Documentation | Discussion]"
        Title: "[Source title]"
        URI: "[Source URL]"
        Date: "[Publication date if available, else N/A]"
        Source_Primacy: "[primary | near-primary]"
        Reproducible_Artifact: "[yes | partial | no | unknown]"
    Mechanism: "[Detailed explanation of the technical mechanism behind the signal]"
    Capability_Delta:
      Type: "[new_capability | cost_reduction | latency_reduction | memory_efficiency | compute_efficiency]"
      Description: "[What becomes possible or materially improved]"
    Integration_Vector:
      Target_System: "[Real target system or pipeline, e.g., Vector DBs, LLM Agents]"
      Integration_Path: "[How this maps into production or research systems]"
      Dependencies:
        - "[Prerequisites]"
      Constraints:
        - "[Known limitations or deployment constraints]"
    Verification:
      C5_REAL_Status: "pass"
      Verified_Claims:
        - "[Claim directly supported by evidence]"
      Open_Uncertainties:
        - "[Known unknowns, missing benchmarks]"
    confidence_score: 0.95
"""

class FrontierIntelSystem:
    """The Sovereign SOTA Vector Engine & Frontier Signal Intelligence System."""

    def __init__(self, engine: Any):
        self.engine = engine
        self.llm = LLMManager()
        self.scraper = ScraperEngine()

    async def scan_source(self, url: str) -> list[dict[str, Any]]:
        """Scrape a URL and extract frontier signals."""
        logger.info("[FRONTIER-INTEL] Scanning source: %s", url)
        try:
            result = await self.scraper.scrape_url(url)
            if result.status != "success":
                logger.error("[FRONTIER-INTEL] Scrape failed for %s: %s", url, result.error)
                return []
            
            text_content = result.content or ""
            if len(text_content.strip()) < 100:
                logger.warning("[FRONTIER-INTEL] Content too short for source %s", url)
                return []

            return await self.analyze_text(text_content, source_url=url)
        except Exception as e:
            logger.exception("[FRONTIER-INTEL] Error scanning source %s: %s", url, e)
            return []

    async def analyze_text(self, text: str, source_url: str = "custom_input") -> list[dict[str, Any]]:
        """Analyze raw text, compute novelty/consensus, and persist detected frontier signals."""
        if not self.llm.available:
            logger.error("[FRONTIER-INTEL] LLM Manager is not available. Ingestion aborted.")
            return []

        prompt = SOTA_PROMPT_TEMPLATE.format(source_url=source_url, text=text[:15000]) # Cap text length to fit context
        
        raw_yaml = await self.llm.complete(
            prompt=prompt,
            system="You are an expert technical intelligence extraction agent. Return raw YAML only.",
            temperature=0.1
        )

        if not raw_yaml:
            logger.warning("[FRONTIER-INTEL] LLM returned empty response.")
            return []

        # Clean markdown wrappers if present
        clean_yaml = raw_yaml.strip()
        if clean_yaml.startswith("```"):
            lines = clean_yaml.split("\n")
            if lines[0].startswith("```yaml") or lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            clean_yaml = "\n".join(lines).strip()

        try:
            nodes = yaml.safe_load(clean_yaml)
            if not isinstance(nodes, list):
                if isinstance(nodes, dict) and "Frontier_Node" in nodes:
                    nodes = [nodes]
                else:
                    logger.error("[FRONTIER-INTEL] Invalid YAML structure parsed (not a list).")
                    return []
        except Exception as e:
            logger.error("[FRONTIER-INTEL] Failed to parse YAML: %s\nRaw output:\n%s", e, clean_yaml)
            return []

        processed_signals = []
        for item in nodes:
            node = item.get("Frontier_Node") if isinstance(item, dict) and "Frontier_Node" in item else item
            if not isinstance(node, dict):
                continue
            
            # Extract core fields
            core_insight = node.get("Core_Insight", "")
            if not core_insight:
                continue

            # 1. Consensus & Novelty Computation via Semantic Search
            novelty_index, consensus_score, phase = await self._calculate_retrieval_metrics(core_insight)

            # Enrich node metadata
            node["novelty_index"] = novelty_index
            node["consensus_score"] = consensus_score
            node["consensus_phase"] = phase

            # 2. Persist signal as a CORTEX fact
            fact_content = f"[{phase.upper()}] Domain: {node.get('Domain')}/{node.get('Subdomain')}. Insight: {core_insight} | Mechanism: {node.get('Mechanism')}"
            
            metadata = {
                "source": source_url,
                "agent_id": "moskv1:frontier_intel",
                "consensus_score": consensus_score,
                "project_id": "frontier_intelligence",
                "domain": node.get("Domain"),
                "subdomain": node.get("Subdomain"),
                "novelty_index": novelty_index,
                "consensus_phase": phase,
                "confidence_score": float(node.get("confidence_score", 0.8)),
                "evidence_primacy": node.get("Evidence", [{}])[0].get("Source_Primacy", "unknown"),
                "reproducible": node.get("Evidence", [{}])[0].get("Reproducible_Artifact", "unknown"),
                "mechanism": node.get("Mechanism"),
                "capability_delta": node.get("Capability_Delta"),
                "integration_vector": node.get("Integration_Vector")
            }

            # Write fact to the tripartite memory system
            fact_id = await self.engine.memory.store(
                tenant_id="default",
                project_id="frontier_intelligence",
                content=fact_content,
                fact_type="fact",
                metadata=metadata,
                layer="semantic"
            )

            node["fact_id"] = fact_id
            processed_signals.append(node)
            logger.info("[FRONTIER-INTEL] Signal logged: %s (Phase: %s, Novelty: %.2f)", core_insight[:50], phase, novelty_index)

        return processed_signals

    async def _calculate_retrieval_metrics(self, core_insight: str) -> tuple[float, float, str]:
        """Query CORTEX facts to determine novelty, consensus, and phase classification."""
        try:
            # Query top 5 similar facts in the frontier_intelligence project
            matches = await self.engine.search(
                query=core_insight,
                project="frontier_intelligence",
                top_k=5,
                tenant_id="default"
            )
        except Exception as e:
            logger.warning("[FRONTIER-INTEL] Semantic search failed: %s", e)
            matches = []

        max_similarity = 0.0
        similar_count = 0
        recent_count = 0
        now = time.time()

        for m in matches:
            # Score is 1.0 - distance
            score = getattr(m, "score", 0.0)
            if score > max_similarity:
                max_similarity = score
            
            if score >= 0.70:
                similar_count += 1
                created_at = getattr(m, "created_at", None)
                # Parse created_at if it's a timestamp
                try:
                    if isinstance(created_at, float | int):
                        if now - created_at < 7 * 86400: # 7 days
                            recent_count += 1
                except Exception:
                    pass

        # Novelty index: inverse of max similarity
        novelty_index = max(0.0, 1.0 - max_similarity)

        # Consensus score calculation: grows with number of similar facts
        import math
        # 1 - e^(-0.5 * N)
        consensus_score = max_similarity * (1.0 - math.exp(-0.5 * similar_count)) if similar_count > 0 else 0.0

        # Consensus Phase Classification
        if novelty_index >= 0.35 and consensus_score < 0.5:
            phase = "pre-consensus"
        elif 0.15 <= novelty_index < 0.35 and 0.5 <= consensus_score < 0.8:
            phase = "emerging"
        else:
            phase = "consensus"

        return round(novelty_index, 3), round(consensus_score, 3), phase

    async def get_signals(self, phase: str | None = None, min_novelty: float = 0.0, top_k: int = 20) -> list[dict[str, Any]]:
        """Query stored signals from database."""
        # Query frontier_intelligence facts directly
        try:
            matches = await self.engine.search(
                query="Domain", # Search broad
                project="frontier_intelligence",
                top_k=top_k * 2,
                tenant_id="default"
            )
        except Exception as e:
            logger.error("[FRONTIER-INTEL] Error fetching signals: %s", e)
            return []

        results = []
        for m in matches:
            meta = getattr(m, "meta", {}) or {}
            c_phase = meta.get("consensus_phase", "unknown")
            novelty = float(meta.get("novelty_index", 0.0))

            if phase and c_phase.lower() != phase.lower():
                continue
            if novelty < min_novelty:
                continue

            results.append({
                "fact_id": getattr(m, "fact_id", None),
                "domain": meta.get("domain"),
                "subdomain": meta.get("subdomain"),
                "core_insight": meta.get("core_insight") or getattr(m, "content", ""),
                "mechanism": meta.get("mechanism"),
                "novelty_index": novelty,
                "consensus_score": meta.get("consensus_score", 0.0),
                "consensus_phase": c_phase,
                "source": meta.get("source"),
                "evidence_primacy": meta.get("evidence_primacy"),
                "reproducible": meta.get("reproducible")
            })

        return results[:top_k]
