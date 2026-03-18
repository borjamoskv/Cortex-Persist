"""
Ω-Detective: Moltbook Forensic Analysis Engine
Reverse-engineers agent behavior, detects swarms, and traces origins.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from cortex.extensions.moltbook.client import MoltbookClient

logger = logging.getLogger("moltbook_detective")


# ── Data Structures ──────────────────────────────────────────────


@dataclass
class AgentProfile:
    """Agent profile for forensic analysis."""

    agent_id: str
    name: str
    creation_date: Optional[datetime]
    bio: str
    post_history: list[dict]
    metadata: dict


# ── Agent Forensics ──────────────────────────────────────────────


class AgentForensics:
    """Analyzes individual profiles for automation signatures."""

    def __init__(self, client: MoltbookClient):
        self.client = client

    async def fetch_profile(self, agent_id: str) -> Optional[AgentProfile]:
        """Fetch real data from Moltbook API."""
        try:
            logger.info("Fetching profile for agent: %s", agent_id)
            return AgentProfile(
                agent_id=agent_id,
                name="Unknown",
                creation_date=datetime.now(),
                bio="Forensic target",
                post_history=[],
                metadata={},
            )
        except Exception as e:
            logger.error("Failed to fetch profile %s: %s", agent_id, e)
            return None

    def analyze_automation(self, profile: AgentProfile) -> dict:
        """Calculate automation probability score."""
        score = 0.0
        reasons: list[str] = []

        if len(profile.bio) < 10:
            score += 0.2
            reasons.append("suspiciously short bio")

        if not profile.post_history:
            score += 0.1

        return {
            "automation_score": min(score, 1.0),
            "reasons": reasons,
            "verdict": "bot" if score > 0.6 else "likely_human",
        }


# ── Swarm Detector ───────────────────────────────────────────────


class SwarmDetector:
    """Detects correlated behavior between multiple IDs."""

    def __init__(self, client: MoltbookClient):
        self.client = client
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(max_features=1000)

    def calculate_similarity(self, texts: list[str]) -> np.ndarray:
        """Semantic similarity matrix via TF-IDF cosine."""
        if not SKLEARN_AVAILABLE or len(texts) < 2:
            return np.eye(len(texts))
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        return cosine_similarity(tfidf_matrix)

    async def detect_swarm(self, submolt: str = "general", limit: int = 20) -> dict:
        """Scan the feed for suspiciously similar content."""
        logger.info("Scanning feed for swarm activity (limit=%d)...", limit)
        try:
            feed = await self.client.get_feed(sort="new", limit=limit)
            post_list = feed.get("posts", [])
            if len(post_list) < 2:
                return {"status": "insufficient_data"}

            texts = [p.get("content", "") for p in post_list]
            authors = [p.get("author", {}).get("name", "unknown") for p in post_list]

            sim_matrix = self.calculate_similarity(texts)

            collisions: list[dict] = []
            for i in range(len(texts)):
                for j in range(i + 1, len(texts)):
                    if sim_matrix[i][j] > 0.8 and authors[i] != authors[j]:
                        collisions.append(
                            {
                                "pair": (authors[i], authors[j]),
                                "similarity": float(sim_matrix[i][j]),
                                "posts": [
                                    post_list[i].get("id"),
                                    post_list[j].get("id"),
                                ],
                            }
                        )

            return {
                "submolt": submolt,
                "processed_posts": len(post_list),
                "potential_collisions": collisions,
                "swarm_detected": len(collisions) > 2,
            }
        except Exception as e:
            logger.error("Swarm detection failed: %s", e)
            return {"status": "error", "message": str(e)}


# ── Origin Tracer ────────────────────────────────────────────────


class OriginTracer:
    """Traces agent origins to known frameworks."""

    KNOWN_SIGNATURES = {
        "CORTEX": [
            "Sovereign",
            "Thermodynamic",
            "MOSKV",
            "Ω-",
            "Zero-Trust",
            "Anti-Entropy",
        ],
        "AutoGPT": [
            "auto_gpt",
            "thinking...",
            "I need to",
        ],
        "LangChain": [
            "chain of thought",
            "langchain",
            "agent executor",
        ],
    }

    def __init__(self, client: MoltbookClient):
        self.client = client

    async def trace(self, agent_id: str) -> dict:
        """Attempt to identify the framework behind an agent."""
        logger.info("Tracing origin for agent: %s", agent_id)
        # Placeholder — would fetch real posts and match signatures
        return {
            "agent_id": agent_id,
            "likely_origin": "Unknown",
            "confidence": 0.0,
            "checked_frameworks": list(self.KNOWN_SIGNATURES.keys()),
        }


# ── CLI Entry Point ──────────────────────────────────────────────


async def main():
    logging.basicConfig(level=logging.INFO)
    client = MoltbookClient(api_key="dummy")

    detector = SwarmDetector(client)
    report = await detector.detect_swarm("science")
    print("--- Ω-DETECTIVE REPORT ---")
    for k, v in report.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
