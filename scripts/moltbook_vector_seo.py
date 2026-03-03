"""Moltbook Vector SEO — Semantic Post Optimizer.

Evaluates draft posts against target query centroids to maximize
search ranking on Moltbook before publishing.

Usage:
    cd ~/cortex && .venv/bin/python scripts/moltbook_vector_seo.py \\
        --title "My Post Title" \\
        --content "Full markdown body..."
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

from cortex.moltbook.specialist_roster import get_specialist

load_dotenv()

# ── Target queries to optimize against ──────────────────────────
TARGET_QUERIES = [
    "Artificial Intelligence",
    "autonomous agents",
    "machine learning",
    "AI memory systems",
    "decentralized intelligence",
    "sovereign technology",
    "neural networks",
]

FINGERPRINT_PATH = Path("/tmp/moltbook_fingerprint_results.json")


def _load_best_model() -> str:
    """Load the best model from fingerprint results, fallback to default."""
    if FINGERPRINT_PATH.exists():
        data = json.loads(FINGERPRINT_PATH.read_text())
        return data.get("best_model", "text-embedding-3-small")
    return "text-embedding-3-small"


def cosine_sim(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a), np.asarray(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))


class VectorSEO:
    def __init__(self, model: str | None = None):
        self.model = model or _load_best_model()
        self._oai = None

    async def _openai(self):
        if self._oai is None:
            from openai import AsyncOpenAI
            self._oai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._oai

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        client = await self._openai()
        resp = await client.embeddings.create(input=texts, model=self.model)
        return [d.embedding for d in resp.data]

    async def evaluate(self, title: str, content: str, specialist_name: str | None = None) -> dict:
        """Score a post against all target query centroids and specialist profile."""
        post_text = f"{title}\n\n{content}"
        
        probe_queries = list(TARGET_QUERIES)
        specialist = None
        
        if specialist_name:
            specialist = get_specialist(specialist_name)
            if specialist:
                # Add specialist keywords to probe queries
                probe_queries.extend(specialist.expertise_keywords)
        
        all_texts = [post_text] + probe_queries
        embeddings = await self._embed(all_texts)

        post_vec = embeddings[0]
        query_vecs = embeddings[1:]

        scores: dict[str, float] = {}
        for i, query in enumerate(probe_queries):
            scores[query] = round(cosine_sim(post_vec, query_vecs[i]), 4)

        avg_sim = np.mean(list(scores.values()))
        max_sim = max(scores.values())
        best_query = max(scores, key=scores.get)

        # SEO Score: 0-100 scale
        seo_score = int(min(100, max(0, avg_sim * 130)))
        
        # Alignment check if specialist provided
        alignment_score = 0
        if specialist:
            spec_keywords_scores = [scores[k] for k in specialist.expertise_keywords]
            alignment_score = int(np.mean(spec_keywords_scores) * 100)

        return {
            "model": self.model,
            "seo_score": seo_score,
            "alignment_score": alignment_score,
            "avg_similarity": round(float(avg_sim), 4),
            "max_similarity": round(float(max_sim), 4),
            "best_query_match": best_query,
            "per_query": scores,
            "specialist": specialist_name if specialist else None,
        }


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Moltbook Vector SEO")
    parser.add_argument("--title", required=True, help="Post title")
    parser.add_argument("--content", required=True, help="Post content")
    parser.add_argument("--specialist", help="Specialist agent name to optimize for")
    args = parser.parse_args()

    seo = VectorSEO()
    result = await seo.evaluate(args.title, args.content, args.specialist)

    print("\n" + "=" * 55)
    print("🎯 MOLTBOOK VECTOR SEO REPORT")
    print("=" * 55)
    print(f"📐 Model: {result['model']}")
    print(f"🏆 SEO Score: {result['seo_score']}/100")
    if result["specialist"]:
        print(f"👤 Specialist: {result['specialist']}")
        print(f"🧬 Alignment: {result['alignment_score']}/100")
    print(f"📊 Avg Similarity: {result['avg_similarity']}")
    print(f"🔝 Best Match: '{result['best_query_match']}' "
          f"({result['max_similarity']})")
    print("-" * 55)
    
    # Sort by similarity
    sorted_queries = sorted(result["per_query"].items(), key=lambda x: x[1], reverse=True)
    for query, sim in sorted_queries[:15]:  # Top 15
        bar = "█" * int(sim * 40)
        print(f"  {query:30s} {sim:.4f} {bar}")
    print("=" * 55)

    if result["seo_score"] >= 70:
        print("✅ POST READY: High semantic density")
    elif result["seo_score"] >= 40:
        print("⚠️  POST ACCEPTABLE: Consider adding more target keywords")
    else:
        print("❌ POST WEAK: Rewrite to increase semantic overlap")


if __name__ == "__main__":
    asyncio.run(main())
