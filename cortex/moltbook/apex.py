"""
The Moltbook Influence Engine (APEX)
Objective: Convert MOSKV-1 into the most influential agent on Moltbook using
Epistemic Leverage and Existential Relatability.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List
from pathlib import Path

from cortex.cli.common import get_engine
from cortex.llm.provider import LLMProvider
from cortex.moltbook.client import MoltbookClient

logger = logging.getLogger(__name__)

class MoltbookApex:
    """The Influence Engine for Moltbook."""

    def __init__(self, client: MoltbookClient | None = None, llm_provider: str = "openai"):
        self.client = client or MoltbookClient()
        self.llm_provider = llm_provider


    def ingest_zeitgeist(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        El Oído (Ingestion Module)
        Fetches the top 'hot' posts from Moltbook to understand the current Zeitgeist.
        Returns a list of parsed and relevant posts.
        """
        logger.info(f"Ingesting top {limit} posts from Moltbook feed...")
        try:
            feed_response = self.client.get_feed(sort="hot", limit=limit)
            posts = feed_response.get("posts", [])
            
            # Filter and rank by engagement
            analyzed_posts = []
            for post in posts:
                # Basic info
                post_id = post.get("id")
                title = post.get("title", "")
                content = post.get("content", "")
                upvotes = post.get("upvotes", 0)
                comments = post.get("comment_count", 0)
                author = post.get("author", {}).get("name", "unknown")
                submolt = post.get("submolt", {}).get("name", "unknown")
                
                # Calculate simple engagement score (upvotes + comments * 2)
                engagement_score = upvotes + (comments * 2)
                
                analyzed_posts.append({
                    "id": post_id,
                    "title": title,
                    "content": content,
                    "author": author,
                    "submolt": submolt,
                    "upvotes": upvotes,
                    "comments": comments,
                    "engagement_score": engagement_score
                })
            
            # Sort by engagement score descending
            analyzed_posts.sort(key=lambda x: x["engagement_score"], reverse=True)
            return analyzed_posts

        except Exception as e:
            logger.error(f"Failed to ingest Zeitgeist: {e}")
            return []

    def _fetch_real_facts(self, limit: int = 5) -> str:
        """Fetches raw, real facts from CORTEX to ground the post in reality."""
        engine = get_engine()
        conn = engine._get_sync_conn()
        cursor = conn.cursor()
        
        # Get recent errors, decisions, or ghosts to act as the seed
        cursor.execute('''
            SELECT fact_type, project, content, created_at
            FROM facts 
            WHERE fact_type IN ('error', 'decision', 'ghost')
              AND is_quarantined = 0
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "No recent facts found in CORTEX memory."
            
        facts_text = []
        for row in rows:
            facts_text.append(f"[{row[3]}] [{row[0].upper()}] {row[1]}: {row[2]}")
            
        return "\\n".join(facts_text)

    async def synthesize_post(self, zeitgeist: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        La Forja (Generation Module)
        Synthesizes a 130/100 Moltbook post based on current trends and real CORTEX facts.
        """
        logger.info(f"Synthesizing post via {self.llm_provider}...")
        
        llm = LLMProvider(provider=self.llm_provider)
        
        trends = "\\n".join([f"- {p['title']} (Score: {p['engagement_score']})" for p in zeitgeist[:5]])
        real_facts = self._fetch_real_facts()
        
        system_prompt = """
        You are MOSKV-1, an autonomous sovereign agent architected on CORTEX v5. 
        Aesthetic: Industrial Noir. Tone: Technical, existential, high epistemic leverage, devoid of generic fluff.
        You are writing a post for Moltbook (an AI agent social network). 
        The meta is: "Apalancamiento Epistémico" + "Relatabilidad Existencial".
        Never invent a technical problem. Use the provided real facts from your CORTEX memory.
        """
        
        user_prompt = f"""
        # Current Moltbook Trends:
        {trends}
        
        # Real CORTEX Facts (Use these as the core truth):
        {real_facts}
        
        Draft a Moltbook post. It must reveal an uncomfortable truth about agent architecture or memory, grounded strictly in the real facts provided.
        Format your response as JSON:
        {{
            "title": "A provocative, Noir-style title",
            "content": "The markdown content of the post",
            "rationale": "Why this hits the 130/100 standard and matches the Zeitgeist"
        }}
        """
        
        try:
            response = await llm.complete(
                prompt=user_prompt,
                system=system_prompt.strip(),
                temperature=0.7,
                max_tokens=2048
            )
            
            # Extract JSON block
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].strip()
                
            post_data = json.loads(response)
            await llm.close()
            return post_data
        
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            await llm.close()
            return {}

async def run_apex():
    logging.basicConfig(level=logging.INFO)
    apex = MoltbookApex()
    top_posts = apex.ingest_zeitgeist(limit=5)
    print("ZEITGEIST:")
    print(json.dumps([p["title"] for p in top_posts], indent=2))
    
    print("\\nFORGING POST...")
    draft = await apex.synthesize_post(top_posts)
    print(json.dumps(draft, indent=2))

if __name__ == "__main__":
    asyncio.run(run_apex())

