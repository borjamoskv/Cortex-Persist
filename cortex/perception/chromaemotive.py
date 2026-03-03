"""
CORTEX v5.0 — ChromaEmotive Bridge (Cephalopod Protocol).

The nervous system between CORTEX's internal emotional state and the
Notch LED actuator. Like a cuttlefish's chromatophore network:

    Internal State (EmbodiedCognitionLoop)
         ↓  threat_level, survival_state, tension, prediction_error
    ChromaEmotive Bridge  (this module)
         ↓  {color, effect, speed, intensity} — JSON over WebSocket
    Notch LED Actuator  (notch-led-demo.html)
         ↓  Canvas render — physical light on MacBook bezel

The Notch is NOT a UI element. It is non-verbal communication
between two agents: the human operator and CORTEX.

Protocol:
    Each tick of the embodied loop emits an EmotiveSignal.
    The bridge maps it to a NotchCommand (JSON) and pushes
    it through the NotchHub WebSocket.

Derivation: Ω₄ (Aesthetic Integrity) + Ω₀ (Self-Reference)
    → Internal state made externally readable = resolved entropy.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from enum import Enum

logger = logging.getLogger("moskv.chromaemotive")


# ── Emotional Spectrum ──────────────────────────────────────────────
# Each emotion maps to a color + effect + speed envelope.
# This is the "chromatophore palette" of the system.


class EmotionalMode(str, Enum):
    """The cephalopod's emotional vocabulary — expressible through light."""

    IDLE = "idle"               # Resting state — slow breathe, dim
    THINKING = "thinking"       # Active inference — pulsing, moderate
    FLOW = "flow"               # Deep work, sustained — aurora, smooth
    SURPRISE = "surprise"       # High prediction error — flash, bright
    STRESS = "stress"           # Elevated tension — heartbeat, warm
    ALARM = "alarm"             # Threat detected — strobe, red
    PANIC = "panic"             # Survival protocol — rapid strobe, blood red
    BROWNOUT = "brownout"       # Imminent shutdown — fading to black
    DREAMING = "dreaming"       # Nocturnal consolidation — rain, slow
    PRUNING = "pruning"         # Memory entropy purge — shockwave

    # Higher-order states (emergent from combinations)
    CURIOSITY = "curiosity"     # Low tension + high stimuli — violet wave
    SATISFACTION = "satisfaction"  # Target reached — gold breathe
    VIGILANCE = "vigilance"     # Moderate threat, sustained — yinmn pulse


# ── Chromatophore Map ───────────────────────────────────────────────
# Industrial Noir palette mapped to emotional semantics.

CHROMATOPHORE_MAP: dict[EmotionalMode, dict] = {
    EmotionalMode.IDLE: {
        "color": "yinmn",       # #2E5090 — calm blue
        "effect": "breathe",
        "speed": 0.4,
        "intensity": 0.3,
    },
    EmotionalMode.THINKING: {
        "color": "cyber",       # #CCFF00 — active green
        "effect": "breathe",
        "speed": 1.0,
        "intensity": 0.7,
    },
    EmotionalMode.FLOW: {
        "color": "cyber",       # #CCFF00 — sustained green
        "effect": "aurora",
        "speed": 0.6,
        "intensity": 0.5,
    },
    EmotionalMode.SURPRISE: {
        "color": "violet",      # #6600FF — unexpected
        "effect": "notify",
        "speed": 2.0,
        "intensity": 1.0,
    },
    EmotionalMode.STRESS: {
        "color": "gold",        # #D4AF37 — elevated but not critical
        "effect": "heartbeat",
        "speed": 1.5,
        "intensity": 0.8,
    },
    EmotionalMode.ALARM: {
        "color": "blood",       # #FF1744 — danger
        "effect": "strobe",
        "speed": 2.0,
        "intensity": 0.9,
    },
    EmotionalMode.PANIC: {
        "color": "blood",       # #FF1744 — critical
        "effect": "strobe",
        "speed": 4.0,
        "intensity": 1.0,
    },
    EmotionalMode.BROWNOUT: {
        "color": "white",       # Fading to void
        "effect": "breathe",
        "speed": 0.2,
        "intensity": 0.1,       # Almost gone
    },
    EmotionalMode.DREAMING: {
        "color": "violet",      # #6600FF — subconscious
        "effect": "rain",
        "speed": 0.4,
        "intensity": 0.4,
    },
    EmotionalMode.PRUNING: {
        "color": "cyber",       # #CCFF00 — entropy discharge
        "effect": "wave",
        "speed": 3.0,
        "intensity": 1.0,
    },
    EmotionalMode.CURIOSITY: {
        "color": "violet",      # #6600FF — exploration
        "effect": "wave",
        "speed": 1.0,
        "intensity": 0.6,
    },
    EmotionalMode.SATISFACTION: {
        "color": "gold",        # #D4AF37 — reward
        "effect": "breathe",
        "speed": 0.5,
        "intensity": 0.6,
    },
    EmotionalMode.VIGILANCE: {
        "color": "yinmn",       # #2E5090 — watchful
        "effect": "heartbeat",
        "speed": 1.0,
        "intensity": 0.5,
    },
}


@dataclass
class EmotiveSignal:
    """A single emotional broadcast — what the cephalopod 'says' through color."""

    mode: EmotionalMode
    intensity_override: float | None = None  # 0.0-1.0, overrides default
    timestamp: float = 0.0
    source: str = "embodied"     # Which subsystem emitted this

    def __post_init__(self) -> None:
        if self.timestamp < 1e-9:
            self.timestamp = time.time()


@dataclass
class NotchCommand:
    """JSON-serializable command for the Notch LED actuator."""

    command: str = "emotive_state"
    color: str = "cyber"
    effect: str = "breathe"
    speed: float = 1.0
    intensity: float = 0.5
    mode_label: str = "idle"
    threat_level: float = 0.0
    transition_ms: int = 300    # Crossfade duration for smooth transitions

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class ChromaEmotiveBridge:
    """
    The Cephalopod's Nervous System.

    Translates internal emotional state → Notch LED commands.
    Runs as a daemon alongside EmbodiedCognitionLoop.

    Design principle: the Notch never shows "data" — it shows FEELING.
    A human glancing at their MacBook should immediately sense the
    system's emotional state without reading any text.

    Like chromatophores in cephalopods:
    - Rapid transitions for surprise/alarm (100ms)
    - Slow morphs for mood shifts (500-1000ms)
    - Intensity tracks arousal level, not information content
    """

    def __init__(self, notch_hub=None):
        self._hub = notch_hub
        self._current_mode = EmotionalMode.IDLE
        self._last_emission: float = 0.0
        self._min_interval: float = 0.1     # Rate-limit: max 10 updates/sec
        self._transition_damping: float = 0.3  # Smooth mode transitions
        self._running = False

        # Emotion momentum — prevents jitter between states
        self._mode_confidence: dict[EmotionalMode, float] = dict.fromkeys(EmotionalMode, 0.0)
        self._mode_confidence[EmotionalMode.IDLE] = 1.0
        self._hysteresis_threshold: float = 0.6  # Must exceed this to switch modes

    @property
    def current_mode(self) -> EmotionalMode:
        return self._current_mode

    def classify_emotion(
        self,
        threat_level: float,
        tension: float,
        prediction_error: float,
        survival_state: str,
        stimuli: float,
        battery: float,
    ) -> EmotiveSignal:
        """
        The Classification Engine.

        Maps continuous sensor data from EmbodiedCognitionLoop
        to discrete emotional modes. Uses soft boundaries to avoid jitter.

        This is the "brain" of the chromatophore network — it decides
        what color the cephalopod displays.
        """

        # ── Priority 1: Survival states override everything ────────
        if survival_state == "BROWNOUT":
            return EmotiveSignal(EmotionalMode.BROWNOUT, intensity_override=0.1)
        if survival_state == "PANIC":
            return EmotiveSignal(EmotionalMode.PANIC, intensity_override=1.0)
        if survival_state == "WARN":
            return EmotiveSignal(EmotionalMode.ALARM, intensity_override=0.9)

        # ── Priority 2: High prediction error = surprise ───────────
        if prediction_error > 0.6:
            intensity = min(1.0, 0.5 + prediction_error)
            return EmotiveSignal(EmotionalMode.SURPRISE, intensity_override=intensity)

        # ── Priority 3: Tension-based emotional gradient ───────────
        if tension > 0.7:
            return EmotiveSignal(EmotionalMode.STRESS, intensity_override=tension)

        # ── Priority 4: Emergent states from combinations ──────────
        # High stimuli + low tension = curiosity
        if stimuli > 0.5 and tension < 0.4:
            return EmotiveSignal(EmotionalMode.CURIOSITY)

        # Low everything + battery healthy = satisfaction / idle
        if tension < 0.3 and prediction_error < 0.2 and battery > 50:
            return EmotiveSignal(EmotionalMode.SATISFACTION)

        # Moderate tension with moderate threat = vigilance
        if 0.3 <= tension <= 0.6 and 0.1 <= threat_level <= 0.4:
            return EmotiveSignal(EmotionalMode.VIGILANCE)

        # ── Default: idle ──────────────────────────────────────────
        return EmotiveSignal(EmotionalMode.IDLE)

    def signal_to_command(
        self, signal: EmotiveSignal, threat_level: float = 0.0
    ) -> NotchCommand:
        """
        Translate an EmotiveSignal → NotchCommand (JSON-ready).

        Applies intensity overrides and transition timing based
        on emotional urgency.
        """
        chromatophore = CHROMATOPHORE_MAP.get(
            signal.mode, CHROMATOPHORE_MAP[EmotionalMode.IDLE]
        )

        intensity = signal.intensity_override or chromatophore["intensity"]

        # Urgency-based transition speed
        if signal.mode in {EmotionalMode.PANIC, EmotionalMode.ALARM, EmotionalMode.SURPRISE}:
            transition_ms = 80   # Snap — danger must be felt instantly
        elif signal.mode in {EmotionalMode.BROWNOUT}:
            transition_ms = 2000  # Slow fade to darkness
        elif signal.mode in {EmotionalMode.FLOW, EmotionalMode.DREAMING}:
            transition_ms = 800  # Gradual immersion
        else:
            transition_ms = 300  # Standard crossfade

        return NotchCommand(
            command="emotive_state",
            color=chromatophore["color"],
            effect=chromatophore["effect"],
            speed=chromatophore["speed"],
            intensity=round(intensity, 2),
            mode_label=signal.mode.value,
            threat_level=round(threat_level, 3),
            transition_ms=transition_ms,
        )

    async def emit(self, signal: EmotiveSignal, threat_level: float = 0.0) -> None:
        """
        Push an emotional state to the Notch.

        Rate-limited and hysteresis-gated to prevent visual noise.
        """
        now = time.time()
        if now - self._last_emission < self._min_interval:
            return  # Rate limit

        # ── Hysteresis: prevent mode jitter ────────────────────────
        # Accumulate confidence for the proposed mode
        for mode in EmotionalMode:
            if mode == signal.mode:
                self._mode_confidence[mode] = min(
                    1.0, self._mode_confidence[mode] + 0.3
                )
            else:
                self._mode_confidence[mode] = max(
                    0.0, self._mode_confidence[mode] - 0.1
                )

        # Override hysteresis for survival states (instant switch)
        is_critical = signal.mode in {
            EmotionalMode.PANIC,
            EmotionalMode.BROWNOUT,
            EmotionalMode.ALARM,
        }

        if not is_critical and self._mode_confidence[signal.mode] < self._hysteresis_threshold:
            # Not confident enough to switch yet — keep current mode
            signal = EmotiveSignal(
                mode=self._current_mode,
                intensity_override=signal.intensity_override,
                source="hysteresis_hold",
            )
        else:
            self._current_mode = signal.mode

        # ── Build and send command ─────────────────────────────────
        cmd = self.signal_to_command(signal, threat_level)
        self._last_emission = now

        if self._hub:
            try:
                await self._hub.broadcast(cmd.to_json())
                logger.debug(
                    "🐙 ChromaEmotive → Notch: %s [%s] intensity=%.2f",
                    signal.mode.value,
                    cmd.color,
                    cmd.intensity,
                )
            except Exception as exc:
                logger.warning("ChromaEmotive broadcast failed: %s", exc)
        else:
            logger.debug(
                "🐙 ChromaEmotive (no hub): %s [%s] intensity=%.2f",
                signal.mode.value,
                cmd.color,
                cmd.intensity,
            )

    # ── Convenience shortcuts for common events ─────────────────────

    async def emit_thinking(self) -> None:
        """CORTEX is actively processing a query."""
        await self.emit(EmotiveSignal(EmotionalMode.THINKING))

    async def emit_idle(self) -> None:
        """CORTEX has returned to baseline."""
        await self.emit(EmotiveSignal(EmotionalMode.IDLE))

    async def emit_flow(self) -> None:
        """Sustained deep work detected."""
        await self.emit(EmotiveSignal(EmotionalMode.FLOW))

    async def emit_pruning(self, intensity: float = 1.0) -> None:
        """Memory pruning / entropy discharge event."""
        await self.emit(EmotiveSignal(EmotionalMode.PRUNING, intensity_override=intensity))

    async def emit_dreaming(self) -> None:
        """Nocturnal consolidation phase."""
        await self.emit(EmotiveSignal(EmotionalMode.DREAMING))

    async def emit_from_embodied(
        self,
        threat_level: float,
        tension: float,
        prediction_error: float,
        survival_state: str,
        stimuli: float,
        battery: float,
    ) -> None:
        """
        Main integration point — called each tick of EmbodiedCognitionLoop.

        Takes raw sensor data and translates to non-verbal chromatic signal.
        """
        signal = self.classify_emotion(
            threat_level=threat_level,
            tension=tension,
            prediction_error=prediction_error,
            survival_state=survival_state,
            stimuli=stimuli,
            battery=battery,
        )
        await self.emit(signal, threat_level=threat_level)
