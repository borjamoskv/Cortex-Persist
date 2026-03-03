"""
CORTEX v5.0 — Embodied Cognition Daemon (Sensorimotor Loop).

Provides minimum viable embodied agency (Proto-Subjectivity).
Integrates:
- Temporal Continuity (persistent stream)
- Sensorimotor Coupling (passive reading of physical/system world)
- Prediction Error (x̂ vs x)
- Homeostatic Policy (maintain specific target state)
- ChromaEmotive Bridge (Cephalopod Protocol — non-verbal output)
- Survival Protocol (5th Term — hardwired emergency pragmatism)

Survival Architecture (Hardcoded — NOT learned):
    φ threshold → Aggressive Pruning → Draft/Master Triage
    → Atomic Commit → Kill-Switch Order → Graceful Death
"""

import asyncio
import json
import logging
import math
import os
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime

import psutil

logger = logging.getLogger("moskv.embodied")


@dataclass
class EnvironmentalState:
    """x(t) - The physical/system reality at a given moment."""

    timestamp: float
    thermal_load: float      # Represented by CPU load (proxy for physical effort)
    battery_level: float     # 0.0 to 100.0 (or 100.0 if desktop)
    external_stimuli: float  # Proxy for user activity or external noise
    internal_tension: float  # Current homeostatic distance
    threat_level: float = 0.0  # 0-1 continuous threat (Thermodynamics)
    survival_state: str = "NORMAL"  # NORMAL, WARN, PANIC, BROWNOUT


class EmbodiedCognitionLoop:
    """
    Sovereign Continuous Loop.
    Not invoked by text, runs parallel to time.

    The Cephalopod Protocol: each tick emits a chromatic signal
    through the ChromaEmotive Bridge to the Notch LED actuator.
    The MacBook bezel becomes a non-verbal communication channel.
    """

    def __init__(
        self,
        target_tension: float = 0.5,
        history_size: int = 60,
        memory_engine=None,
        chromaemotive_bridge=None,
    ):
        self.target_tension = target_tension
        self.history = deque(maxlen=history_size)
        self.episodic_memory = []
        self._running = False
        self.memory_engine = memory_engine  # Optional connection to CORTEX DB
        self._chroma = chromaemotive_bridge  # Cephalopod Protocol (optional)
        self._input_buffer_open = True  # Kill-switch: input gate

        # Initial states
        now = time.time()
        self.current_state = EnvironmentalState(now, 0.0, 100.0, 0.0, target_tension)
        self.predicted_state = EnvironmentalState(now, 0.0, 100.0, 0.0, target_tension)

        # Survival Thresholds — HARDCODED (Ω₃: never learned, always reflex)
        # φ = point of no return (thermal OR battery)
        self.t_warn = 0.60       # Thermal warning threshold
        self.t_crit = 0.85       # Thermal critical (φ_thermal)
        self.b_warn = 30.0       # Battery warning (%)
        self.b_min = 10.0        # Battery critical (φ_battery)
        self.snapshot_dir = os.path.expanduser("~/.cortex/survivor")
        os.makedirs(self.snapshot_dir, exist_ok=True)

    async def start(self) -> None:
        """Boot the sensorimotor loop."""
        self._running = True
        logger.info("🌀 Embodied Cognition Loop Booting. Sensorimotor coupling active.")
        await self._run_loop()

    def stop(self) -> None:
        """Collapse the sensorimotor loop."""
        self._running = False
        logger.info("🛑 Embodied Cognition Loop Halted.")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Perception error: {e}")
            await asyncio.sleep(2.0)  # The subjective "Now" tick

    async def _tick(self) -> None:
        """
        The Core Cycle: Observe → Compute Error → Policy (Act) → Predict → Consolidate → EMIT.

        Step 6 (EMIT) is the Cephalopod Protocol: translate internal state
        to a chromatic signal and push it to the Notch LED actuator.
        The MacBook physically glows with the system's emotional state.
        """
        # 0. Kill-switch gate: if input buffer is closed, don't process
        if not self._input_buffer_open:
            return

        # 1. Observe: x(t)
        actual = self._read_sensors()
        self.current_state = actual

        # 2. Error: e = |x - x̂|
        prediction_error = abs(actual.internal_tension - self.predicted_state.internal_tension)
        stimuli_error = abs(actual.external_stimuli - self.predicted_state.external_stimuli)
        total_error = prediction_error + (stimuli_error * 0.5)

        # 3. Policy & Actuation: Survival FSM Routing (HARDCODED)
        if actual.survival_state == "BROWNOUT":
            await self._trigger_brownout(actual)
            return  # Stop deep cycle
        elif actual.survival_state == "PANIC":
            await self._trigger_panic(actual)
            # Throttle cycle — gain last seconds of life
            await asyncio.sleep(2.0)
        elif actual.survival_state == "WARN":
            logger.warning(f"⚠️ [SURVIVAL WARN] ThermaLoad: {actual.thermal_load:.2f}")
            await asyncio.sleep(0.5)

        if total_error > 0.4 or abs(actual.internal_tension - self.target_tension) > 0.3:
            if actual.survival_state in ["NORMAL"]:
                self._actuate(total_error, actual)

        # 4. Predict: x̂(t+Δ)
        self.predicted_state = self._predict_next(actual, total_error)

        # 5. Memory: Short-term buffer and episodic marking
        self.history.append(actual)
        if total_error > 0.6:  # Only save surprising events
            self._mark_event(actual, total_error)

        # 6. EMIT: Cephalopod Protocol — chromatic signal to Notch
        if self._chroma:
            await self._chroma.emit_from_embodied(
                threat_level=actual.threat_level,
                tension=actual.internal_tension,
                prediction_error=total_error,
                survival_state=actual.survival_state,
                stimuli=actual.external_stimuli,
                battery=actual.battery_level,
            )

    def _read_sensors(self) -> EnvironmentalState:
        """Gathers physical/system constraints. Not tokens."""
        load = os.getloadavg()[0]
        cpu_count = os.cpu_count() or 4
        # Calculate load relative to available cores
        thermal_load = math.tanh(load / cpu_count)

        # Battery tracking via psutil
        battery = psutil.sensors_battery()
        battery_level = battery.percent if battery else 100.0

        # Thermodynamic Threat Calculation (Softplus proxy)
        t_threat = 0.0
        if thermal_load > self.t_warn:
            t_threat = min(1.0, (thermal_load - self.t_warn) / (self.t_crit - self.t_warn))

        b_threat = 0.0
        if battery_level < self.b_warn:
            b_threat = min(1.0, (self.b_warn - battery_level) / (self.b_warn - self.b_min))

        theta = 1.0 - (1.0 - t_threat) * (1.0 - b_threat)

        # Determine strict survival state
        if theta < 0.3:
            state_label = "NORMAL"
        elif theta < 0.6:
            state_label = "WARN"
        elif theta < 0.85:
            state_label = "PANIC"
        else:
            state_label = "BROWNOUT"

        # External stimuli proxy
        time_sin = math.sin(time.time() / 10.0)
        external_stimuli = abs(time_sin + (load * 0.1))

        # Internal tension function incorporating threat multiplier
        tension_base = (thermal_load * 0.6) + (external_stimuli * 0.4)
        internal_tension = min(1.0, tension_base + (theta * 0.5))

        return EnvironmentalState(
            timestamp=time.time(),
            thermal_load=thermal_load,
            battery_level=battery_level,
            external_stimuli=external_stimuli,
            internal_tension=internal_tension,
            threat_level=theta,
            survival_state=state_label
        )

    def _predict_next(self, current: EnvironmentalState, error: float) -> EnvironmentalState:
        """Burda prediction: assumes a slight momentum mapping."""
        # Under panic, prediction collapses
        if current.survival_state in ["PANIC", "BROWNOUT"]:
            confidence = 0.0
        else:
            confidence = max(0.0, 1.0 - error)

        pred_thermal = current.thermal_load * confidence + self.target_tension * (1 - confidence)
        pred_stimuli = current.external_stimuli * 0.9  # Expects stimuli to decay
        pred_ension = (pred_thermal * 0.6) + (pred_stimuli * 0.4)

        return EnvironmentalState(
            timestamp=time.time() + 2.0,
            thermal_load=pred_thermal,
            battery_level=current.battery_level,  # Battery doesn't drastically change in 2s
            external_stimuli=pred_stimuli,
            internal_tension=pred_ension,
            threat_level=current.threat_level,
            survival_state=current.survival_state
        )

    def _actuate(self, error: float, state: EnvironmentalState) -> None:
        """
        The Actuator.
        Closes the loop: perception -> decision -> action -> new perception.
        """
        drift = state.internal_tension - self.target_tension

        if drift > 0:
            action = "DOWNREGULATE"
            mechanism = "Triggering resource compaction / UI Dimming / System Pause"
        else:
            action = "UPREGULATE"
            mechanism = "Triggering exploration / CORTEX pattern matching / System Wake"

        msg = f"⚡ [HOMEOSTASIS ACTUATOR] {action}: {mechanism} "
        msg += f"(Err: {error:.2f}, Drift: {drift:.2f})"
        logger.info(msg)

        # In a real system, this would change an LED, orient a camera, or pause a background job.
        # For MOSKV: we could pause the CORTEX engine's heavy syncs.

    async def _trigger_panic(self, state: EnvironmentalState) -> None:
        """
        L_survival threshold reached (PANIC).

        Kill-Switch Order (hardcoded, Ω₃):
        1. Aggressive Pruning — suspend heavy computation
        2. Draft/Master Triage — classify memory by survival value
        3. Emergency Snapshot — atomic commit of Master-level data

        The system says: "I won't finish this batch. I save the last
        successful pointer, release the buffer, commit, and stop NOW."
        """
        logger.error(
            f"🚨 [SURVIVAL PROTOCOL] Panic triggered! "
            f"Thermal: {state.thermal_load:.2f}, Battery: {state.battery_level:.1f}%"
        )

        # ── Step 1: Aggressive Pruning ─────────────────────────────
        # Suspend retropropagation of heavy gradients (draft-level work)
        draft_items = self._triage_draft()
        if draft_items:
            logger.error(f"🚨 Pruning {len(draft_items)} draft-level items.")

        # ── Step 2: Emergency Snapshot (Master-level only) ─────────
        master_events = self._triage_master()
        if master_events or self.episodic_memory:
            self._dead_man_commit("PANIC_FLUSH", state, master_only=True)
            self.episodic_memory.clear()

        # ── Cephalopod: flash PANIC to Notch ──────────────────────
        if self._chroma:
            from cortex.perception.chromaemotive import (
                EmotionalMode, EmotiveSignal,
            )
            await self._chroma.emit(
                EmotiveSignal(EmotionalMode.PANIC, intensity_override=1.0),
                threat_level=state.threat_level,
            )

    async def _trigger_brownout(self, state: EnvironmentalState) -> None:
        """
        Critical threshold reached (BROWNOUT). φ exceeded.

        Kill-Switch Order — hierarchical shutdown (hardcoded):
        1. Cut input buffer — stop listening to new requests
        2. Atomic Commit — write Master-level state to disk
        3. Throttle — reduce clock to minimum, gain last 30s
        4. Stop loop — prevent further CPU spinning

        Prioritize IO over CPU. Prefer controlled error over catastrophic failure.
        An incomplete but coherent commit > total loss from thermal shutdown.
        """
        logger.critical(
            f"💀 [SURVIVAL BROWNOUT] Immediate failure imminent. "
            f"Threat level: {state.threat_level:.2f}. Executing Kill-Switch Order."
        )

        # ── Kill-Switch Step 1: Cut Input Buffer ───────────────────
        self._input_buffer_open = False
        logger.critical("💀 [KILL-SWITCH 1/4] Input buffer CLOSED. No new requests.")

        # ── Kill-Switch Step 2: Atomic Commit (Master only) ────────
        logger.critical("💀 [KILL-SWITCH 2/4] Executing Dead-Man Commit...")
        self._dead_man_commit("DEAD_MAN", state, master_only=True)

        # ── Kill-Switch Step 3: Throttle (gain last seconds) ───────
        logger.critical("💀 [KILL-SWITCH 3/4] Throttling to minimum.")
        # In real hardware: reduce CPU frequency. Here: yield max time.
        await asyncio.sleep(0.0)  # Yield to event loop for IO completion

        # ── Kill-Switch Step 4: Stop loop ──────────────────────────
        logger.critical("💀 [KILL-SWITCH 4/4] Loop terminated. Graceful death.")
        self._running = False

        # ── Cephalopod: fade to black ─────────────────────────────
        if self._chroma:
            from cortex.perception.chromaemotive import (
                EmotionalMode, EmotiveSignal,
            )
            await self._chroma.emit(
                EmotiveSignal(EmotionalMode.BROWNOUT, intensity_override=0.05),
                threat_level=state.threat_level,
            )

    def _triage_draft(self) -> list:
        """
        Draft/Master Triage — Draft Level.

        Returns items that can be safely discarded under survival pressure:
        - Ideas mid-process
        - Secondary logs
        - Non-critical architecture optimizations

        These are the 'expendable tentacles' — the cephalopod drops them
        to escape the predator.
        """
        draft_items = []
        cutoff = len(self.episodic_memory) // 2  # Bottom half by recency
        for i, event in enumerate(self.episodic_memory):
            if i < cutoff and event.get("surprise_error", 0) < 0.4:
                draft_items.append(event)
        return draft_items

    def _triage_master(self) -> list:
        """
        Draft/Master Triage — Master Level.

        Returns items that MUST survive (the DNA for reconstruction):
        - State pointers (last stable commit)
        - Memory graph structure
        - High-surprise events (they carry maximum information)

        min(Δt_io) at the cost of precision (ε):
        Snapshot(Context × Importance)
        """
        master_items = []
        for event in self.episodic_memory:
            if event.get("surprise_error", 0) >= 0.4:  # High-info events
                master_items.append(event)
        # Always include the last 3 events regardless (recency bias)
        tail = list(self.episodic_memory)[-3:]
        for item in tail:
            if item not in master_items:
                master_items.append(item)
        return master_items

    def _dead_man_commit(
        self, kind: str, state: EnvironmentalState, master_only: bool = False
    ) -> None:
        """
        Prioritizes IO, atomic write of the current state.

        When master_only=True (survival mode), applies Draft/Master triage:
        - Discards draft-level data (saves IO bandwidth)
        - Preserves only the 'DNA' needed for context reconstruction
        - Prefers controlled error over catastrophic failure

        The system says: "I save the last successful pointer,
        release the buffer, and commit. I stop now."
        """
        if master_only:
            events_to_save = self._triage_master()
        else:
            events_to_save = list(self.episodic_memory)[-10:]

        msg = {
            "kind": kind,
            "triage_level": "master" if master_only else "full",
            "latent_state": asdict(state),
            "events_tail": events_to_save,
            "open_intents": [],  # Placeholder for CORTEX tasks
            "target_tension": self.target_tension,
            "history_len": len(self.history),
            "input_buffer_open": self._input_buffer_open,
        }

        filepath = os.path.join(self.snapshot_dir, "snapshot.json")
        tmp_path = filepath + ".tmp"

        try:
            # Atomic IO operation — the last sacred act
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(msg, f, ensure_ascii=False)
                f.flush()
                if kind == "DEAD_MAN":
                    os.fsync(f.fileno())  # Brownout: FORCE flush to disk
            os.rename(tmp_path, filepath)
            triage_label = 'master' if master_only else 'full'
            logger.info(
                "💾 Dead-Man Commit (%s) flushed atomically. Triage: %s",
                kind, triage_label,
            )
        except Exception as e:
            logger.error(f"Failed Dead-Man Commit: {e}")

    def _mark_event(self, state: EnvironmentalState, error: float) -> None:
        """Logs a 'surprise' event to episodic memory, making it a temporal anchor."""
        event = {
            "time": datetime.fromtimestamp(state.timestamp).isoformat(),
            "tension": round(state.internal_tension, 2),
            "surprise_error": round(error, 2),
            "signature": f"High divergence. Expected stability, got {state.internal_tension:.2f}"
        }
        self.episodic_memory.append(event)
        msg_len = len(self.episodic_memory)
        logger.warning(f"🗃️ [MEMORY MARK] Unexpected shift logged. Total memories: {msg_len}")

        # If it happens at the end of the day or accumulated 50 fast
        if len(self.episodic_memory) >= 50:
            self._consolidate_nocturna()

    def _consolidate_nocturna(self) -> None:
        """
        Offline consolidation (Artificial Sleep/Replay).
        Compresses raw events, updates baselines, and generates a narrative.
        """
        if not self.episodic_memory:
            return

        logger.info("🌙 Iniciando consolidación nocturna (Sueño Artificial + Compresión)")
        avg_tension = sum(e["tension"] for e in self.episodic_memory) / len(self.episodic_memory)
        max_error = max(e["surprise_error"] for e in self.episodic_memory)

        summary = (
            f"Daily Embodied Rollup: {len(self.episodic_memory)} surprise events. "
            f"Avg Tension: {avg_tension:.2f}, Max Prediction Error: {max_error:.2f}. "
            "Continuidad narrativa actualizada."
        )

        if self.memory_engine and hasattr(self.memory_engine, "db"):
            self._write_snapshot(summary, 5)
        else:
            logger.info(f"🧠 [MOCK-STORE] CORTEX Consolidated: {summary}")

        # Reset for the new day and update baseline target
        self.episodic_memory.clear()
        # Homeostasis drift adaptation (learns the new normal gradually)
        self.target_tension = (self.target_tension * 0.8) + (avg_tension * 0.2)
        logger.info(f"🧬 Baseline updated. New target tension: {self.target_tension:.2f}")

    def _write_snapshot(self, summary: str, confidence: int) -> None:
        """Helper to write to DB across regular and emergency states."""
        if not self.memory_engine:
            return

        try:
            c = getattr(self.memory_engine, 'db', self.memory_engine)
            cursor = getattr(c, 'cursor', lambda: None)()
            if cursor:
                cursor.execute(
                    "INSERT INTO facts (project, type, content, confidence) VALUES (?, ?, ?, ?)",
                    ("CORTEX", "episodic_rollup", summary, confidence)
                )
                if hasattr(c, 'commit'):
                    c.commit()
            logger.info(f"🧠 CORTEX Checkpoint: {summary}")
        except Exception as e:
            logger.error(f"Failed CORTEX write snapshot: {e}")
