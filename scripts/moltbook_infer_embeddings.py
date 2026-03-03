"""Moltbook Embedding Fingerprint — Pearson + Spearman Correlation.

Exploits the exposed `relevance` field in /search to infer the embedding
model used by Moltbook's ranking pipeline.

Usage:
    cd ~/cortex && .venv/bin/python scripts/moltbook_infer_embeddings.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from scipy.stats import pearsonr, spearmanr

from cortex.moltbook.client import MoltbookClient, MoltbookRateLimited

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | 🔬 %(levelname)s: %(message)s",
)
logger = logging.getLogger("EmbeddingFingerprint")

# ── Candidate models to test (OpenAI API) ──────────────────────
CANDIDATE_MODELS = [
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
]

# ── Diverse probe queries for statistical power ─────────────────
PROBE_QUERIES = [
    "Artificial Intelligence",
    "autonomous agents memory",
    "decentralized systems networking",
    "machine learning embeddings",
    "consciousness philosophy AI",
]

RESULTS_PATH = Path("/tmp/moltbook_fingerprint_results.json")

_MARK_RE = re.compile(r"</?mark>")


def _strip_mark(text: str) -> str:
    """Remove <mark>...</mark> highlight tags Moltbook injects."""
    return _MARK_RE.sub("", text)


def cosine_sim(v1: list[float], v2: list[float]) -> float:
    a, b = np.asarray(v1), np.asarray(v2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


class EmbeddingFingerprinter:
    def __init__(self, proxy: str | None = None):
        self.moltbook = MoltbookClient(proxy=proxy)
        self._oai = None

    async def _openai(self):
        if self._oai is None:
            from openai import AsyncOpenAI
            self._oai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._oai

    async def _fetch_search(self, query: str, max_retries: int = 3) -> list[dict]:
        """Fetch search results with relevance scores (rate-limit aware)."""
        for attempt in range(max_retries):
            try:
                data = await self.moltbook.search(query, limit=20)
                break
            except MoltbookRateLimited as exc:
                wait = exc.retry_after + 3
                logger.warning(
                    "Rate limited on '%s'. Waiting %ds (attempt %d/%d)",
                    query, wait, attempt + 1, max_retries,
                )
                await asyncio.sleep(wait)
            except Exception as exc:
                logger.warning("Search failed for '%s': %s", query, exc)
                return []
        else:
            logger.error("Exhausted retries for '%s'", query)
            return []

        items = data.get("items", data.get("results", []))
        if items:
            keys = list(items[0].keys())
            logger.info("Item keys: %s", keys)

        out: list[dict] = []
        for item in items:
            relevance = item.get("relevance", item.get("score"))
            content = _strip_mark(
                item.get("content", "")
                or item.get("text", "")
                or item.get("title", "")
            )
            if relevance is not None and content:
                out.append({
                    "content": content,
                    "relevance": float(relevance),
                    "author": (item.get("author") or {}).get("name", "?"),
                })
        return out

    async def _embed_batch(
        self, texts: list[str], model: str,
    ) -> list[list[float]]:
        client = await self._openai()
        resp = await client.embeddings.create(input=texts, model=model)
        return [d.embedding for d in resp.data]

    async def fingerprint(self):
        """Run the full multi-query fingerprint analysis."""
        logger.info("=" * 60)
        logger.info("🕵️  MOLTBOOK EMBEDDING FINGERPRINT — COMMENCING")
        logger.info("=" * 60)

        # Phase 1: Collect all data points with query-item mapping
        query_items: dict[str, list[dict]] = {}  # query -> items
        all_pairs: list[tuple[int, float, str]] = []  # (query_idx, score, text)

        for qi, query in enumerate(PROBE_QUERIES):
            logger.info("🔎 Probing: '%s'", query)
            items = await self._fetch_search(query)
            logger.info("   → %d items with relevance", len(items))
            query_items[query] = items
            for it in items:
                all_pairs.append((qi, it["relevance"], it["content"]))
            await asyncio.sleep(2.0)  # polite jitter between queries

        if len(all_pairs) < 5:
            logger.error(
                "Only %d data points. Need ≥5 for correlation.",
                len(all_pairs),
            )
            await self.moltbook.close()
            return

        logger.info(
            "\n📊 Total data points: %d across %d queries",
            len(all_pairs), len(PROBE_QUERIES),
        )

        texts = [p[2] for p in all_pairs]
        moltbook_scores = [p[1] for p in all_pairs]
        query_indices = [p[0] for p in all_pairs]

        results: dict[str, dict] = {}

        for model in CANDIDATE_MODELS:
            try:
                logger.info("🧠 Embedding with %s...", model)
                all_input = list(PROBE_QUERIES) + texts
                embeddings = await self._embed_batch(all_input, model)

                query_embeddings = embeddings[:len(PROBE_QUERIES)]
                doc_embeddings = embeddings[len(PROBE_QUERIES):]

                # Compute cosine sim: each doc vs its source query
                local_scores: list[float] = []
                for i, qi in enumerate(query_indices):
                    sim = cosine_sim(query_embeddings[qi], doc_embeddings[i])
                    local_scores.append(sim)

                # Trim to same length
                min_len = min(len(moltbook_scores), len(local_scores))
                ms = moltbook_scores[:min_len]
                ls = local_scores[:min_len]

                if min_len < 3:
                    logger.warning("Too few paired points for %s", model)
                    continue

                pearson_r, pearson_p = pearsonr(ms, ls)
                spearman_r, spearman_p = spearmanr(ms, ls)

                results[model] = {
                    "pearson_r": round(pearson_r, 4),
                    "pearson_p": round(pearson_p, 6),
                    "spearman_r": round(spearman_r, 4),
                    "spearman_p": round(spearman_p, 6),
                    "n_pairs": min_len,
                }

                logger.info(
                    "   ► %s: Pearson=%.4f (p=%.4f) | Spearman=%.4f (p=%.4f)",
                    model, pearson_r, pearson_p, spearman_r, spearman_p,
                )
            except Exception as exc:
                logger.error("   ❌ %s failed: %s", model, exc)

        # ── Conclusion ───────────────────────────────────────────
        if not results:
            logger.error("No models produced correlations.")
            await self.moltbook.close()
            return

        best = max(results, key=lambda m: results[m]["spearman_r"])
        best_r = results[best]["spearman_r"]

        print("\n" + "=" * 60)
        if best_r > 0.85:
            print(f"🎯 FINGERPRINT POSITIVO: Motor core ≈ {best}")
            print(f"   Spearman ρ = {best_r}")
        elif best_r > 0.6:
            print(f"⚠️  FINGERPRINT PROBABLE: Alineación con {best}")
            print(f"   Spearman ρ = {best_r} (probable re-ranker)")
        else:
            print("❌ ASIMETRÍA NEGATIVA: No concuerda con modelos OpenAI")
            print(f"   Mejor candidato: {best} (ρ={best_r})")
            print("   → Probable modelo HuggingFace o BM25 puro")
        print("=" * 60)

        # ── Persist results ──────────────────────────────────────
        output = {
            "timestamp": asyncio.get_event_loop().time(),
            "queries": PROBE_QUERIES,
            "total_pairs": len(all_pairs),
            "models": results,
            "best_model": best,
            "best_spearman": best_r,
            "raw_scores_sample": [
                {"moltbook": ms[i], "local": ls[i]}
                for i in range(min(10, min_len))
            ],
        }
        RESULTS_PATH.write_text(json.dumps(output, indent=2))
        logger.info("📁 Results saved to %s", RESULTS_PATH)

        await self.moltbook.close()


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Moltbook Embedding Fingerprint")
    parser.add_argument("--proxy", help="Proxy URL (e.g. http://user:pass@host:port)")
    args = parser.parse_args()
    
    fp = EmbeddingFingerprinter(proxy=args.proxy)
    await fp.fingerprint()


if __name__ == "__main__":
    asyncio.run(main())
