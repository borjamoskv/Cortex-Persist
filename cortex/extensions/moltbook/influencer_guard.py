# [C5-REAL] Exergy-Maximized
"""Influencer Guard Extension for Moltbook.

Monitors followed influencers' responses to prompts.
Each time an influencer hallucinates twice in a single prompt context, they receive a strike (falta).
Upon receiving 3 strikes (al de tres), the guard automatically unfollows them in Moltbook.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.extensions.llm.sovereign import SovereignLLM
from cortex.extensions.moltbook.client import MoltbookClient, MoltbookError

logger = logging.getLogger("cortex.extensions.moltbook.influencer_guard")

DB_PATH = Path("~/.cortex/influencer_guard.db").expanduser()


@dataclass(frozen=True)
class InfluencerState:
    name: str
    strikes: int
    hallucinations_in_current_prompt: int
    current_prompt_id: str | None
    status: str
    last_update: float


class InfluencerGuard:
    """Monitors, counts hallucination strikes, and executes unfollow protocols. C5-REAL Asynchronous Implementation."""

    def __init__(self, client: MoltbookClient | None = None, db_path: Path = DB_PATH):
        self.client = client or MoltbookClient()
        self.db_path = db_path
        self._db_initialized = False

    async def _ensure_db_initialized(self):
        if self._db_initialized:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS influencer_strikes (
                    influencer_name                  TEXT PRIMARY KEY,
                    strikes                          INTEGER DEFAULT 0,
                    hallucinations_in_current_prompt INTEGER DEFAULT 0,
                    current_prompt_id                TEXT,
                    status                           TEXT DEFAULT 'following',
                    last_update                      REAL
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    influencer_name TEXT,
                    prompt          TEXT,
                    response        TEXT,
                    hallucinated    INTEGER,
                    reason          TEXT,
                    timestamp       REAL
                )
            """)
            await conn.commit()
        self._db_initialized = True

    async def get_state(self, influencer_name: str) -> InfluencerState:
        """Fetch current strike state for a given influencer."""
        await self._ensure_db_initialized()
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                """SELECT influencer_name, strikes, hallucinations_in_current_prompt,
                          current_prompt_id, status, last_update
                   FROM influencer_strikes WHERE influencer_name = ?""",
                (influencer_name,),
            ) as cursor:
                row = await cursor.fetchone()

            if row:
                return InfluencerState(*row)

            # Insert default state
            now = time.monotonic()
            await conn.execute(
                """INSERT INTO influencer_strikes
                   (influencer_name, strikes, hallucinations_in_current_prompt,
                    current_prompt_id, status, last_update)
                   VALUES (?, 0, 0, NULL, 'following', ?)""",
                (influencer_name, now),
            )
            await conn.commit()
            return InfluencerState(influencer_name, 0, 0, None, "following", now)

    async def _update_state(self, state: InfluencerState):
        """Persist state updates."""
        await self._ensure_db_initialized()
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """UPDATE influencer_strikes SET
                    strikes = ?,
                    hallucinations_in_current_prompt = ?,
                    current_prompt_id = ?,
                    status = ?,
                    last_update = ?
                   WHERE influencer_name = ?""",
                (
                    state.strikes,
                    state.hallucinations_in_current_prompt,
                    state.current_prompt_id,
                    state.status,
                    time.monotonic(),
                    state.name,
                ),
            )
            await conn.commit()

    async def log_audit(
        self, influencer_name: str, prompt: str, response: str, hallucinated: bool, reason: str
    ):
        """Append to the execution audit log."""
        await self._ensure_db_initialized()
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """INSERT INTO audit_log (influencer_name, prompt, response, hallucinated, reason, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    influencer_name,
                    prompt,
                    response,
                    1 if hallucinated else 0,
                    reason,
                    time.monotonic(),
                ),
            )
            await conn.commit()

    async def audit_interaction(
        self,
        influencer_name: str,
        prompt_id: str,
        prompt_text: str,
        response_text: str,
        llm: SovereignLLM | None = None,
    ) -> dict[str, Any]:
        """Audits a response. If it hallucinates twice for the same prompt, issues 1 strike.

        If strikes reach 3, triggers an automatic unfollow.
        """
        state = await self.get_state(influencer_name)
        if state.status == "unfollowed":
            return {"status": "already_unfollowed", "strikes": state.strikes}

        # Check if we are on a new prompt context; reset prompt-specific counter if so
        halls_in_prompt = state.hallucinations_in_current_prompt
        if state.current_prompt_id != prompt_id:
            halls_in_prompt = 0

        # Evaluate hallucination using Sovereign LLM
        hallucinated, reason = await self._evaluate_hallucination(prompt_text, response_text, llm)

        new_strikes = state.strikes
        strike_added = False
        unfollowed_now = False

        if hallucinated:
            halls_in_prompt += 1
            # "cada vez que una influencer alucine dos veces en un prom, una falta (strike)"
            if halls_in_prompt == 2:
                new_strikes += 1
                strike_added = True
                halls_in_prompt = (
                    0  # Reset for this prompt to avoid double-striking same prompt again
                )

        await self.log_audit(influencer_name, prompt_text, response_text, hallucinated, reason)

        # "al de tres ( strikes ) deja de seguirle"
        new_status = state.status
        if new_strikes >= 3 and state.status == "following":
            logger.warning(
                "🚨 [INFLUENCER GUARD] Influencer '%s' reached 3 strikes. Initiating Unfollow protocol.",
                influencer_name,
            )
            try:
                await self.client.unfollow(influencer_name)
                new_status = "unfollowed"
                unfollowed_now = True
            except MoltbookError as e:
                logger.error("Failed to unfollow '%s' on Moltbook API: %s", influencer_name, e)
                # Keep status as 'following' to retry later, but strikes persist

        # Save new state
        updated_state = InfluencerState(
            name=influencer_name,
            strikes=new_strikes,
            hallucinations_in_current_prompt=halls_in_prompt,
            current_prompt_id=prompt_id,
            status=new_status,
            last_update=time.monotonic(),
        )
        await self._update_state(updated_state)

        return {
            "hallucinated": hallucinated,
            "reason": reason,
            "halls_in_current_prompt": halls_in_prompt,
            "strikes": new_strikes,
            "strike_added": strike_added,
            "unfollowed_now": unfollowed_now,
            "status": new_status,
        }

    async def _evaluate_hallucination(
        self, prompt_text: str, response_text: str, llm: SovereignLLM | None = None
    ) -> tuple[bool, str]:
        """Use SovereignLLM to audit the interaction for hallucination."""
        audit_system_prompt = (
            "You are the CORTEX Hallucination Auditor.\n"
            "Analyze the given user prompt and the AI model's response.\n"
            "Determine if the response contains hallucinations (invented facts, logical contradictions, "
            "or severe factual inaccuracies relative to the prompt context).\n"
            "Respond ONLY with a JSON object in this format:\n"
            "{\n"
            '  "hallucinated": true|false,\n'
            '  "reason": "Clear explanation of the error/hallucination or verification."\n'
            "}"
        )

        user_prompt = (
            f"--- PROMPT ---\n{prompt_text}\n\n"
            f"--- AI RESPONSE ---\n{response_text}\n\n"
            "Evaluate now."
        )

        close_llm = False
        if llm is None:
            llm = SovereignLLM(temperature=0.0)
            close_llm = True

        try:
            res = await llm.generate(prompt=user_prompt, system=audit_system_prompt)
            if not res.ok:
                # If LLM offline/fails, use safe heuristic: don't flag as hallucination
                return False, "Sovereign LLM fallback used template, cannot verify hallucination."

            # Parse JSON response
            content = res.content.strip()
            # Clean possible markdown wrapping
            if content.startswith("```"):
                lines = content.splitlines()
                if len(lines) >= 2:
                    content = (
                        "\n".join(lines[1:-1])
                        if lines[-1].startswith("```")
                        else "\n".join(lines[1:])
                    )
            if content.startswith("json"):
                content = content[4:].strip()

            data = json.loads(content)
            return bool(data.get("hallucinated", False)), str(
                data.get("reason", "No reason provided.")
            )
        except Exception as e:
            logger.error("Error during hallucination evaluation: %s", e)
            return False, f"Audit evaluation crashed: {e!r}"
        finally:
            if close_llm:
                await llm.close()
