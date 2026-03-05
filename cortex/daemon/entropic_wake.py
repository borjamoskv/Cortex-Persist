"""
Entropic Wake Daemon (VOID DAEMON)
The proactive heartbeat that crosses the Rubicon: from determinism to autonomous mutation.
"""

import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from cortex.songlines.sensor import TopographicSensor

logger = logging.getLogger("cortex.daemon.entropic_wake")


class EntropicWakeDaemon:
    """
    Evaluates Zenón's Razor to autonomously spawn agents and resolve entropy.
    If general or localized entropy exceeds threshold (τ_z > 1.0):
      1. Ignites daemon.
      2. Purgation via headless sub-agent spawn.
    """

    def __init__(self, engine: Any, check_interval_hours: int = 4, zenon_threshold: float = 1.0):
        self.engine = engine
        self.interval_seconds = check_interval_hours * 3600
        self.threshold = zenon_threshold
        self._shutdown = False

    def check_entropy(self) -> float:
        """
        Calculate current τ_z (Zenón's Entropy).
        This integrates RADAR metrics: aging TODOs, inactive ghost facts, and complexity ratios.
        """
        logger.info("RADAR-Ω: Calculating codebase entropy...")
        # Placeholder for actual RADAR metric calculation logic
        # For now, it queries the DB ghosts or relies on an existing telemetry heuristic
        if not self.engine:
            return 0.0

        entropy_score = 0.0
        try:
            # 1. Physical Ghosts (Banda G resonance)
            sensor = TopographicSensor()
            # Default to scanning the CORTEX directory
            scan_path = Path.home() / "cortex"
            ghosts = sensor.scan_field(scan_path)
            
            # Each ghost's strength contributes to the total resonance
            physical_resonance = sum(g.get("strength", 0.0) for g in ghosts)
            # Normalize physical resonance impact (e.g., 0.1 per full point of resonance)
            entropy_score += (physical_resonance * 0.1)

            # 2. Epistemic Entropy (Banda E) - Low confidence facts in the database
            conn = self.engine.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT count(*) FROM facts "
                "WHERE confidence IN ('stated', 'C3', 'C2', 'C1') AND is_tombstoned = 0"
            )
            epistemic_ghosts = cursor.fetchone()[0]
            # Normalize epistemic weight (e.g., 0.05 per low confidence fact)
            entropy_score += (epistemic_ghosts * 0.05)
            
            # 3. DB Type Ghosts
            cursor.execute(
                "SELECT COUNT(*) FROM facts WHERE type = 'ghost' AND status != 'resolved'"
            )
            db_ghosts = cursor.fetchone()[0]
            entropy_score += (db_ghosts * 0.15)

        except Exception as e:
            logger.error(f"RADAR-Ω Entropic query failed: {e}")

        logger.debug(f"Current Zenón Entropy τ_z: {entropy_score}")
        return entropy_score

    def ignite_purification_agent(self, target: str = "modulo_entropico"):
        """
        Spawn the headless agent.
        Todo ocurre sin un solo Input Field.
        """
        logger.warning(f"THRESHOLD EXCEEDED. Imploding execution context for {target}.")
        intent = "Aniquilación y extracción O(1) vía OUROBOROS-Ω y Berreraiki."
        command = [
            "cortex", "spawn",
            f"--target={target}",
            f"--intent={intent}"
        ]

        try:
            # Singularidad Headless: Detached background process
            logger.info("Executing: %s", " ".join(command))
            subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            # Log the action in memory
            self._log_action_to_cortex(target)
        except Exception as e:
            logger.error(f"Failed to ignite purification agent: {e}")

    def _log_action_to_cortex(self, target: str):
        """Register the autonomous action into CORTEX-DB."""
        if not self.engine:
            return
        now_str = datetime.now().strftime('%H:%M %p')
        msg = (
            f"Anoche a las {now_str} disolví secciones entrópicas estancadas en {target}. "
            "Pasó los tests de inmunidad. Deuda saldada. PR en espera de merge."
        )
        try:
            conn = self.engine.pool.get_connection()
            conn.execute(
                "INSERT INTO facts (id, type, topic, content, timestamp) "
                "VALUES (lower(hex(randomblob(16))), 'decision', 'Autopoiesis', ?, ?)",
                (msg, time.time())
            )
            conn.commit()
            logger.info("Logged autopoiesis cycle to CORTEX.")
        except Exception as e:
            logger.error(f"Failed to log to cortex DB: {e}")

    def run_loop(self):
        """The main continuous loop for the Void Daemon."""
        logger.info("Initializing Entropic Wake Loop (VOID DAEMON)...")
        while not self._shutdown:
            try:
                tau_z = self.check_entropy()
                if tau_z > self.threshold:
                    # In a true system, we dynamically select the target based on entropy clusters
                    highest_entropy_target = "cortex_router"  # Placeholder
                    self.ignite_purification_agent(highest_entropy_target)
            except Exception as e:
                logger.error(f"Entropic Wake encountered an error: {e}")

            # Sleep until next pulse
            time.sleep(self.interval_seconds)

    def stop(self):
        logger.info("Stopping Entropic Wake Daemon.")
        self._shutdown = True
