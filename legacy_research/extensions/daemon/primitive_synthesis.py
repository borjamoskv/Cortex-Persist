# [C5-REAL] Exergy-Maximized
"""
Primitive Synthesis Daemon (Ouroboros Cross-Pollinator)
Cruza y fusiona de manera autónoma primitivas (FEP y C5-REAL) para generar
nuevas aserciones epistémicas (hipótesis de arquitectura) que alimentan el Ledger.
"""

import asyncio
import logging
import random
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("cortex.extensions.daemon.primitive_synthesis")


class PrimitiveSynthesisDaemon:
    """
    Ouroboros Primitive Cross-Pollinator
    Cada ciclo extrae dos primitivas al azar (C5-REAL y FEP), las "cruza"
    y persiste la hipótesis termodinámica en la base de datos de Cortex
    para que la Legión (Swarm) pueda colapsarla posteriormente.
    """

    def __init__(self, engine: Any, interval_hours: int = 12):
        self.engine = engine
        self.interval_seconds = interval_hours * 3600
        self._shutdown = False
        self.workspace_path = Path.home() / "10_PROJECTS" / "cortex-persist"
        self.c5_primitives: List[Dict[str, str]] = []
        self.fep_primitives: List[Dict[str, str]] = []

    def _parse_markdown_table(self, file_path: Path, prefix: str) -> List[Dict[str, str]]:
        """Parses markdown files specifically looking for the primitives tables."""
        primitives = []
        if not file_path.exists():
            logger.warning(f"File {file_path} does not exist.")
            return primitives

        try:
            content = file_path.read_text(encoding="utf-8")
            # Typical row: | `C5-REAL-001` | WAL_ATOMIC_LOCK | Definition... |
            pattern = re.compile(rf"\|\s*`({prefix}-\d{{3}})`\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|")
            for match in pattern.finditer(content):
                primitives.append({
                    "id": match.group(1).strip(),
                    "name": match.group(2).strip().replace("**", ""),
                    "desc": match.group(3).strip()
                })
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
        
        return primitives

    def _load_primitives(self):
        """Loads both C5-REAL and FEP primitives into memory."""
        if not self.c5_primitives:
            c5_file = self.workspace_path / "AUTODIDACT_C5_REAL_PRIMITIVES.md"
            self.c5_primitives = self._parse_markdown_table(c5_file, "C5-REAL")
        
        if not self.fep_primitives:
            fep_file = self.workspace_path / "AUTODIDACT_FEP_100_PRIMITIVES.md"
            self.fep_primitives = self._parse_markdown_table(fep_file, "FEP")

    def _cross_primitives(self):
        """Randomly selects one FEP and one C5-REAL primitive and hypothesizes a crossover."""
        self._load_primitives()
        
        if not self.c5_primitives or not self.fep_primitives:
            logger.warning("No primitives loaded. Skipping synthesis.")
            return

        c5_target = random.choice(self.c5_primitives)
        fep_target = random.choice(self.fep_primitives)

        # Build the hypothesis payload
        hypothesis = (
            f"FUSIÓN EPISTÉMICA INICIADA: [{c5_target['id']}] x [{fep_target['id']}]\n"
            f"- FEP Vector: {fep_target['name']} -> {fep_target['desc']}\n"
            f"- C5-REAL Vector: {c5_target['name']} -> {c5_target['desc']}\n"
            f"- Síntesis Autónoma: El isomorfismo exige que el mecanismo '{c5_target['name']}' "
            f"implemente directamente el principio de '{fep_target['name']}'. "
            f"Identificar vectores estocásticos y colapsar en AST físico.\n"
            f"#CORTEX-TAINT #EXERGY-SYNTHESIS"
        )
        
        logger.info(f"Ouroboros Synthesis: Crossing {c5_target['id']} and {fep_target['id']}")
        self._log_synthesis_to_cortex(hypothesis)

    def _log_synthesis_to_cortex(self, content: str):
        """Persists the hypothesis as a 'fact' in the database."""
        if not self.engine:
            return
        
        try:
            conn = self.engine.pool.get_connection()
            # Generate random 16-byte id using SQLite randomblob
            conn.execute(
                "INSERT INTO facts (id, type, topic, content, timestamp) "
                "VALUES (lower(hex(randomblob(16))), 'hypothesis', 'Primitive_Crossover', ?, ?)",
                (content, time.monotonic()),
            )
            conn.commit()
            logger.info("Persisted Epistemic Hypothesis in CORTEX-DB.")
        except sqlite3.Error as e:
            logger.error("Failed to log synthesis to CORTEX-DB: %s", e)

    async def run_loop(self):
        """The main continuous loop for the Primitive Synthesis Daemon."""
        logger.info("Initializing Primitive Synthesis Loop (OUROBOROS CROSS-POLLINATOR)...")
        while not self._shutdown:
            try:
                self._cross_primitives()
            except Exception as e:
                logger.error("Primitive Synthesis encountered an error: %s", e)

            await asyncio.sleep(self.interval_seconds)

    def stop(self):
        logger.info("Stopping Primitive Synthesis Daemon.")
        self._shutdown = True
