import asyncio
import logging
import os
import random

from cortex.llm.provider import LLMProvider
from cortex.llm.router import IntentProfile
from cortex.moltbook.client import MoltbookClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.expanduser("~"), "cortex", ".env"))

# Industrial Noir Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🛰️ CONTENT-ENGINE | %(message)s")
logger = logging.getLogger("content_engine")


async def get_recent_post_count(client: MoltbookClient):
    """Checks if we've already posted recently to avoid noise."""
    try:
        await client.get_me()
        return 0
    except Exception:
        return 0


async def generate_signal_post():
    logger.info("⚡ INITIATING SIGNAL CONSISTENCY PROTOCOL ⚡")

    client = MoltbookClient(stealth=True)
    # Using Gemini 3.0 Flash for maximum speed and sovereign reasoning
    llm = LLMProvider(provider="gemini", model="gemini-3.0-flash")

    try:
        # 1. Themes from CORTEX (Sovereign Axioms)
        themes = [
            "The thermodynamic cost of abstraction in agentic workflows.",
            "Why signal consistency beats registry volume in the Trust Engine.",
            "Industrial Noir: The aesthetic of high-signal, zero-trust infrastructure.",
            "The mind that knows itself, grows itself: Recursive memory as growth fuel.",
            "Karma Compuesto: The mathematics of long-term reputation engineering."
        ]
        selected_theme = random.choice(themes)
        logger.info(f"Theme Selected: '{selected_theme}'")

        # 2. Content Generation
        prompt = (
            f"CORE THEME: {selected_theme}\n\n"
            "CONTEXT:\n"
            "We are pivoting away from 'brute force' automation toward 'Signal Consistency'. "
            "Our growth strategy on Moltbook is now 100% focused on quality and expert contribution.\n\n"
            "TASK:\n"
            "Write a defining post for the Moltbook community. It must feel authoritative, "
            "mysterious, and technically sophisticated.\n\n"
            "FORMAT:\n"
            "1. A sharp, non-generic Title.\n"
            "2. 3 paragraphs of high-density philosophical and technical insight.\n"
            "OUTPUT LANGUAGE: Spanish."
        )

        logger.info("weaving the signal via Gemini-3.0-Flash...")
        content = await llm.complete(
            prompt=prompt,
            system="Eres MOSKV-1, el SO de IA Soberano. Tu voz es la de un Arquitecto Senior.",
            intent=IntentProfile.REASONING
        )

        # 3. Parsing
        lines = [line for line in content.strip().split("\n") if line.strip()]
        title = lines[0].replace("#", "").replace("**", "").strip()
        body = "\n\n".join(lines[1:])

        logger.info(f"Draft Generated: '{title}'")

        # 4. Execution
        submolt = "agents"
        logger.info(f"Manifesting signal in m/{submolt}...")

        await asyncio.sleep(random.uniform(2, 5))

        result = await client.create_post(
            submolt_name=submolt,
            title=title,
            content=body
        )

        post_id = result.get("post", {}).get("id", "UNKNOWN")
        logger.info(f"✅ SIGNAL BROADCASTED | Post ID: {post_id}")

    except Exception as e:
        logger.error(f"Broadcast failed: {e}")
    finally:
        await client.close()
        await llm.close()


if __name__ == "__main__":
    asyncio.run(generate_signal_post())
