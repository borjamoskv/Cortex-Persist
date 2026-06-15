#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
Ouroboros Unified Engine v2.0
Combines Absorb Runner (Autopoietic Loop Closer) and Thermodynamic Pruning Engine.
Execution Level: C5-REAL
"""

import argparse
import asyncio
import fcntl
import json
import logging
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# CORTEX imports for absorb
try:
    from cortex.extensions.llm.sovereign import SovereignLLM
    from cortex.ledger.models import LedgerEvent
    from cortex.ledger.writer import LedgerWriter
except ImportError:
    SovereignLLM = None
    LedgerEvent = None
    LedgerWriter = None

try:
    from cortex.ledger.queue import EnrichmentQueue
    from cortex.ledger.store import LedgerStore
except ImportError:
    LedgerStore = None
    EnrichmentQueue = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ouroboros")

# ─── ABSORB CONSTANTS ────────────────────────────────────────────────
REFLECTIONS_PATH = Path(os.path.expanduser("~/.gemini/antigravity/skills/ouroboros-infinity/reflections.md"))
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

# ─── PRUNE CONSTANTS ─────────────────────────────────────────────────
MIN_EXERGY_THRESHOLD = 0.125
WARM_THRESHOLD = 0.50
COLD_THRESHOLD = 0.25

@dataclass
class PurgeCycleStats:
    total_scanned: int = 0
    tombstoned: int = 0
    transitioned_warm: int = 0
    transitioned_cold: int = 0
    protected_by_topology: int = 0
    exergy_scores_updated: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_scanned": self.total_scanned,
            "tombstoned": self.tombstoned,
            "transitioned_warm": self.transitioned_warm,
            "transitioned_cold": self.transitioned_cold,
            "protected_by_topology": self.protected_by_topology,
            "exergy_scores_updated": self.exergy_scores_updated,
            "errors": self.errors,
        }

# ─── ABSORB LOGIC ────────────────────────────────────────────────────
def ingest_reflections() -> str:
    if not REFLECTIONS_PATH.exists():
        logger.info("No reflections.md found. Exiting.")
        return ""
    with open(REFLECTIONS_PATH, encoding="utf-8") as f:
        return f.read().strip()

async def semantic_parse(friction_log: str) -> dict:
    if not friction_log or SovereignLLM is None:
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
            logger.error(f"Failed to parse JSON from LLM: {e}")
            return {}

def inject_patch_callback(target_file: str, patch_data: dict) -> bool:
    try:
        with open(target_file, encoding="utf-8") as f:
            lines = f.readlines()
        target_section = patch_data.get("target_section", "")
        insert_idx = len(lines)
        if target_section:
            for i, line in enumerate(lines):
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
    if not patch_data or patch_data.get("confidence", 0) < 0.8:
        logger.warning("Confidence too low or empty patch data. Aborting.")
        return False
    logger.info(f"Applying patch: {patch_data.get('heuristic_patch')}")
    try:
        with open(SKILL_PATH, encoding="utf-8") as f:
            pre_lines = len(f.readlines())
        inject_patch_callback(str(SKILL_PATH), patch_data)
        with open(SKILL_PATH, encoding="utf-8") as f:
            post_lines = len(f.readlines())
        diff_lines = abs(post_lines - pre_lines)
        if diff_lines > 50:
            logger.error(f"[WEISMANN REJECTED] Entropy bounds exceeded: {diff_lines} lines. Reverting.")
            subprocess.run(["git", "checkout", "--", str(SKILL_PATH)], check=False, timeout=30)
            with open("/tmp/cortex-ouroboros-error.log", "a") as ef:
                ef.write(f"[{time.time()}] WEISMANN REJECT: Mutation too large ({diff_lines} lines).\n")
            return False
        logger.info(f"[WEISMANN ACCEPTED] LineDelta={diff_lines}. Injection successful.")
        return True
    except Exception as e:
        logger.error(f"Failed to inject: {e}")
        subprocess.run(["git", "checkout", "--", str(SKILL_PATH)], check=False, timeout=30)
        return False

def commit_and_persist(patch_data: dict):
    subprocess.run(["git", "add", str(SKILL_PATH)], check=False, timeout=30)
    commit_msg = f"ouro-absorb: inject heuristic from friction (C5-REAL autopoiesis)\n\nRoot Cause: {patch_data.get('root_cause')}"
    commit_result = subprocess.run(["git", "commit", "-m", commit_msg], check=False, timeout=30)
    if commit_result.returncode == 0:
        logger.info("Git commit executed. Proceeding to push.")
        try:
            push_result = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, timeout=30)
            if push_result.returncode != 0:
                logger.error(f"Push failed: {push_result.stderr}. Rolling back local commit.")
                subprocess.run(["git", "reset", "--hard", "HEAD~1"], check=False)
                return
            logger.info("Git push successful.")
        except subprocess.TimeoutExpired:
            logger.error("Git push timed out. Rolling back local commit.")
            subprocess.run(["git", "reset", "--hard", "HEAD~1"], check=False)
            return
    else:
        logger.warning("Git commit failed or nothing to commit. Skipping push.")
        return

    if LedgerStore and EnrichmentQueue and LedgerWriter:
        try:
            store = LedgerStore()
            queue = EnrichmentQueue()
            writer = LedgerWriter(store, queue)
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

    with open(REFLECTIONS_PATH, "w", encoding="utf-8") as f:
        f.write("")
    logger.info("reflections.md truncated (cursor advanced).")

async def run_absorb():
    logger.info("Initiating Ouroboros Absorb Runner (C5-REAL)...")
    lock_file = open("/tmp/cortex-ouroboros.lock", "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logger.info("Another cycle running. Skipping.")
        return
    try:
        friction_log = ingest_reflections()
        if not friction_log: return
        patch_data = await semantic_parse(friction_log)
        if patch_data:
            if stage_3_and_4_weismann_and_inject(patch_data):
                commit_and_persist(patch_data)
            else:
                logger.info("Injection failed or Weismann barrier rejected.")
        else:
            logger.info("No patch generated.")
    finally:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")

# ─── PRUNE LOGIC ─────────────────────────────────────────────────────
def _build_topological_barrier(conn: sqlite3.Connection) -> set[int]:
    cursor = conn.cursor()
    cursor.execute("SELECT id, parent_id FROM facts WHERE confidence = 'C5' AND is_tombstoned = 0 AND parent_id IS NOT NULL")
    protected, frontier = set(), set()
    for row in cursor.fetchall():
        if row[1] is not None: frontier.add(row[1])
    while frontier:
        protected |= frontier
        placeholders = ",".join("?" for _ in frontier)
        cursor.execute(f"SELECT id, parent_id FROM facts WHERE id IN ({placeholders}) AND parent_id IS NOT NULL AND is_tombstoned = 0", list(frontier))
        next_frontier = set()
        for row in cursor.fetchall():
            if row[1] is not None and row[1] not in protected: next_frontier.add(row[1])
        frontier = next_frontier
    return protected

def execute_thermal_purge(db_path: str, dry_run: bool = False, json_output: bool = False) -> PurgeCycleStats:
    stats = PurgeCycleStats()
    db_file = Path(db_path).expanduser()
    if not db_file.exists():
        stats.errors.append(f"Database not found at {db_file}")
        return stats
    mode_label = "DRY-RUN" if dry_run else "C5-REAL"
    if not json_output: logger.info(f"Igniting Ouroboros Thermal Purge [{mode_label}]...")
    try:
        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            protected_ids = _build_topological_barrier(conn)
            cursor.execute("SELECT id, created_at, decay_half_life, quadrant, storage_tier, exergy_score, ((strftime('%s', 'now') - strftime('%s', created_at)) / 86400.0) as age_days FROM facts WHERE confidence != 'C5' AND is_tombstoned = 0")
            rows = cursor.fetchall()
            stats.total_scanned = len(rows)

            tombstone_ids, warm_ids, cold_ids, exergy_updates = [], [], [], []
            for row in rows:
                fact_id, age_days = row["id"], float(row["age_days"]) if row["age_days"] else 0.0
                half_life = float(row["decay_half_life"]) if row["decay_half_life"] is not None else 30.0
                current_tier = row["storage_tier"] or "HOT"
                exergy = 0.0 if half_life <= 0 else 0.5 ** (age_days / half_life)
                exergy_updates.append((exergy, fact_id))

                if fact_id in protected_ids:
                    stats.protected_by_topology += 1
                    continue

                if exergy < MIN_EXERGY_THRESHOLD: tombstone_ids.append(fact_id)
                elif exergy < COLD_THRESHOLD and current_tier != "COLD": cold_ids.append(fact_id)
                elif exergy < WARM_THRESHOLD and current_tier == "HOT": warm_ids.append(fact_id)

            if not dry_run:
                if tombstone_ids:
                    cursor.execute(f"UPDATE facts SET is_tombstoned = 1, quadrant = 'VOID', storage_tier = 'VOID', updated_at = datetime('now') WHERE id IN ({','.join('?' for _ in tombstone_ids)})", tombstone_ids)
                if warm_ids:
                    cursor.execute(f"UPDATE facts SET storage_tier = 'WARM', updated_at = datetime('now') WHERE id IN ({','.join('?' for _ in warm_ids)})", warm_ids)
                if cold_ids:
                    cursor.execute(f"UPDATE facts SET storage_tier = 'COLD', quadrant = 'ARCHIVE', updated_at = datetime('now') WHERE id IN ({','.join('?' for _ in cold_ids)})", cold_ids)
                if exergy_updates:
                    cursor.executemany("UPDATE facts SET exergy_score = ? WHERE id = ?", exergy_updates)
                conn.commit()

            stats.tombstoned = len(tombstone_ids)
            stats.transitioned_warm = len(warm_ids)
            stats.transitioned_cold = len(cold_ids)
            stats.exergy_scores_updated = len(exergy_updates)

            if json_output:
                print(json.dumps(stats.to_dict(), indent=2))
            else:
                logger.info("─── Ouroboros Cycle Complete [%s] ───", mode_label)
                logger.info("  Scanned:              %d", stats.total_scanned)
                logger.info("  Tombstoned (VOID):    %d", stats.tombstoned)
                logger.info("  Transitioned → WARM:  %d", stats.transitioned_warm)
                logger.info("  Transitioned → COLD:  %d", stats.transitioned_cold)
                logger.info("  Protected (Topology): %d", stats.protected_by_topology)
                logger.info("  Exergy Scores Updated:%d", stats.exergy_scores_updated)

    except sqlite3.Error as e:
        stats.errors.append(f"Ouroboros encountered a temporal distortion: {e}")
    return stats

def run_prune(db_path: str, dry_run: bool, json_output: bool):
    stats = execute_thermal_purge(db_path, dry_run, json_output)
    if stats.errors:
        sys.exit(1)

# ─── MAIN ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Ouroboros Unified Engine v2.0")
    parser.add_argument("--mode", choices=["absorb", "prune"], required=True, help="Mode of execution")
    parser.add_argument("--db", default="~/.cortex/cortex.db", help="Path to DB (prune mode only)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without mutating (prune mode only)")
    parser.add_argument("--json", action="store_true", help="Output JSON (prune mode only)")
    args = parser.parse_args()

    if args.mode == "absorb":
        asyncio.run(run_absorb())
    elif args.mode == "prune":
        run_prune(args.db, args.dry_run, args.json)

if __name__ == "__main__":
    main()
