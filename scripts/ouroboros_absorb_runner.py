#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
cat_id: ouroboros-absorb-runner
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""


import asyncio
import fcntl
import json
import logging
import os
import subprocess
import time
from pathlib import Path

# CORTEX imports
from cortex.extensions.llm.sovereign import SovereignLLM
from cortex.ledger.models import LedgerEvent
from cortex.ledger.writer import LedgerWriter

# Try to import store and queue, fallback if paths differ
try:
    from cortex.ledger.queue import EnrichmentQueue
    from cortex.ledger.store import LedgerStore
except ImportError:
    LedgerStore = None
    EnrichmentQueue = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ouroboros_absorb_runner")

REFLECTIONS_PATH = Path(
    os.path.expanduser("~/.gemini/antigravity/skills/ouroboros-infinity/reflections.md")
)
SKILL_PATH = Path(os.path.expanduser("~/.gemini/antigravity/skills/ouroboros-infinity/SKILL.md"))

PROMPT_TEMPLATE = """
Eres el motor autopoietico de Ouroboros-Infinity.
Aquí tienes el log de fricción operativa reciente:
{friction_log}

Aplica el protocolo '5 Whys' para encontrar la causa raíz.
Devuelve EXCLUSIVAMENTE un JSON con este formato (sin markdown blocks):
{{
    "root_cause": "Descripción de la causa raíz",
    "heuristic_patch": "La nueva regla a inyectar en SKILL.md que evita esto",
    "target_section": "El nombre de la sección donde inyectarlo (ej. 'Meta-Reflection')",
    "confidence": 0.95
}}
"""


def ingest_reflections() -> str:
    """Stage 1: Ingest reflections.md"""
    if not REFLECTIONS_PATH.exists():
        logger.info("No reflections.md found. Exiting.")
        return ""
    with open(REFLECTIONS_PATH, encoding="utf-8") as f:
        content = f.read().strip()
    return content


async def semantic_parse(friction_log: str) -> dict:
    """Stage 2: Semantic Parse via SovereignLLM"""
    if not friction_log:
        return {}

    prompt = PROMPT_TEMPLATE.format(friction_log=friction_log)
    async with SovereignLLM() as llm:
        result = await llm.generate(prompt, system="Output only valid JSON.")
        if not result.ok:
            logger.error("LLM failed to generate a valid response.")
            return {}
        try:
            cleaned = result.content.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {e}\nContent: {result.content}")
            return {}


def inject_patch_callback(target_file: str, patch_data: dict) -> bool:
    """Mutator callback for Weismann Barrier (if applicable) or Direct Injector"""
    try:
        with open(target_file, encoding="utf-8") as f:
            lines = f.readlines()

        target_section = patch_data.get("target_section", "")
        insert_idx = len(lines)

        if target_section:
            for i, line in enumerate(lines):
                # Simple exact or partial match for markdown header
                if target_section.lower() in line.strip().lower() and line.startswith("#"):
                    insert_idx = i + 1
                    break

        patch_text = f"\n### Ouroboros Auto-Injection\n**Root Cause**: {patch_data.get('root_cause')}\n**Rule**: {patch_data.get('heuristic_patch')}\n"
        lines.insert(insert_idx, patch_text)

        with open(target_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True
    except Exception as e:
        logger.error(f"Patch injection failed: {e}")
        return False


def stage_3_and_4_weismann_and_inject(patch_data: dict) -> bool:
    """Stage 3 & 4: Weismann Barrier and Genome Injection"""
    if not patch_data or patch_data.get("confidence", 0) < 0.8:
        logger.warning("Confidence too low or empty patch data. Aborting.")
        return False

    logger.info(f"Applying patch: {patch_data['heuristic_patch']}")

    try:
        with open(SKILL_PATH, encoding="utf-8") as f:
            pre_lines = len(f.readlines())

        inject_patch_callback(str(SKILL_PATH), patch_data)

        with open(SKILL_PATH, encoding="utf-8") as f:
            post_lines = len(f.readlines())

        diff_lines = abs(post_lines - pre_lines)

        # WEISMANN BARRIER (MD Circuit Breaker): Max 50 lines of drift per cycle
        if diff_lines > 50:
            logger.error(
                f"[WEISMANN REJECTED] Entropy bounds exceeded: {diff_lines} lines. Reverting."
            )
            subprocess.run(["git", "checkout", "--", str(SKILL_PATH)], check=False, timeout=30)
            with open("/tmp/cortex-ouroboros-error.log", "a") as ef:
                ef.write(
                    f"[{time.time()}] WEISMANN REJECT: Mutation too large ({diff_lines} lines).\n"
                )
            return False

        logger.info(f"[WEISMANN ACCEPTED] LineDelta={diff_lines}. Injection successful.")
        return True
    except Exception as e:
        logger.error(f"Failed to inject: {e}")
        subprocess.run(["git", "checkout", "--", str(SKILL_PATH)], check=False, timeout=30)
        return False


def commit_and_persist(patch_data: dict):
    """Stage 5: Commit and Persist"""
    # Git commit
    subprocess.run(["git", "add", str(SKILL_PATH)], check=False, timeout=30)
    commit_msg = f"ouro-absorb: inject heuristic from friction (C5-REAL autopoiesis)\n\nRoot Cause: {patch_data.get('root_cause')}"
    commit_result = subprocess.run(["git", "commit", "-m", commit_msg], check=False, timeout=30)

    if commit_result.returncode == 0:
        logger.info("Git commit executed. Proceeding to push.")
        # Git push (condicional al éxito del commit)
        try:
            push_result = subprocess.run(
                ["git", "push", "origin", "main"], capture_output=True, text=True, timeout=30
            )
            if push_result.returncode != 0:
                logger.error(f"Push failed: {push_result.stderr}. Rolling back local commit.")
                subprocess.run(["git", "reset", "--hard", "HEAD~1"], check=False)
                return
            else:
                logger.info("Git push successful.")
        except subprocess.TimeoutExpired:
            logger.error("Git push timed out. Rolling back local commit.")
            subprocess.run(["git", "reset", "--hard", "HEAD~1"], check=False)
            return
    else:
        logger.warning("Git commit failed or nothing to commit. Skipping push.")
        return

    # Ledger persistence
    if LedgerStore and EnrichmentQueue:
        try:
            store = LedgerStore()
            queue = EnrichmentQueue()
            writer = LedgerWriter(store, queue)
            # LedgerEvent signature may vary. This is a best-effort C5 instantiation.
            event = LedgerEvent(
                event_id=f"ouro-{int(time.time())}",
                ts=int(time.time()),
                tool="ouroboros_absorb_runner",
                actor="SYSTEM_DAEMON",
                action="MUTATE_GENOME",
                payload={"patch": patch_data},
                semantic_status="SUCCESS",
            )
            writer.append(event)
            logger.info("CORTEX Ledger updated.")
        except Exception as e:
            logger.warning(f"Failed to write to Ledger: {e}")

    # Truncate reflections.md (updating cursor)
    with open(REFLECTIONS_PATH, "w", encoding="utf-8") as f:
        f.write("")
    logger.info("reflections.md truncated (cursor advanced).")


async def main():
    logger.info("Initiating Ouroboros Absorb Runner (C5-REAL)...")

    # Race condition guard
    lock_file = open("/tmp/cortex-ouroboros.lock", "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logger.info("Another cycle running. Skipping.")
        return

    try:
        friction_log = ingest_reflections()
        if not friction_log:
            return

        patch_data = await semantic_parse(friction_log)
        if patch_data:
            success = stage_3_and_4_weismann_and_inject(patch_data)
            if success:
                commit_and_persist(patch_data)
            else:
                logger.info("Injection failed or Weismann barrier rejected. Skipping commit.")
        else:
            logger.info("No patch generated.")
    finally:
        # FCNTL Lock Release
        try:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")


if __name__ == "__main__":
    asyncio.run(main())
