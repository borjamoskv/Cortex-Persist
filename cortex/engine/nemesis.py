from __future__ import annotations

import datetime
import logging
import re

import aiosqlite

from cortex.database.core import connect as db_connect
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.signals.bus import AsyncSignalBus, SignalBus

logger = logging.getLogger("cortex.nemesis")


class NemesisRejection(Exception):
    """Raised when a fact violates the 130/100 standard and is rejected by Nemesis."""

    pass


class NemesisProtocol:
    """Enforces the 130/100 standard on all incoming memory facts."""

    _rejection_history: dict[str, int] = {}  # Vector -> Count (Ω₃ Cellular Memory)
    _attack_vectors: dict[str, str] = {}  # Snapshot of suspected attacks

    # Anti-patterns that trigger immediate rejection
    ANTI_PATTERNS = [
        (
            r"console\.log\(.*?\)",
            "Debugging efímero (console.log). Usa logging estructurado temporal o destrúyelo.",
        ),
        (
            r"t.o.d.o:|f.i.x.m.e:|h.a.c.k:",
            "Marcadores de deuda técnica detectados. Resuélvelo ahora, no lo dejes para después.",
        ),
        (
            r"copy-paste|copiado de|stackoverflow",
            "Código no asimilado. Viola el Axioma I (Causal Over Correlation).",
        ),
        (
            r"por si acaso|just in case",
            "Abstracción defensiva ('por si acaso'). Viola el Axioma IV: Densidad Infinita.",
        ),
        (
            r"bootstrap|tailwind default",
            "Estética genérica detectada. Exigimos Industrial Noir 130/100.",
        ),
    ]

    NEMESIS_PATH = "/Users/borjafernandezangulo/cortex/nemesis.md"

    @classmethod
    def _load_dynamic_antibodies(cls) -> list[tuple[str, str]]:
        """Parses nemesis.md to extract dynamically generated antibodies."""
        dynamic_rules = []
        try:
            with open(cls.NEMESIS_PATH) as f:
                content = f.read()
                # Simple table parser for | Vector | Antibody | Date |
                # Matches rows like: | `pattern` | reason | date |
                matches = re.findall(r"\|\s*`(.+?)`\s*\|\s*(.+?)\s*\|", content)
                for pattern, reason in matches:
                    # Escape backslashes if they were doubled in md
                    pattern = pattern.replace("\\\\", "\\")
                    dynamic_rules.append((pattern, reason.strip()))
        except FileNotFoundError:
            pass
        return dynamic_rules

    @classmethod
    def analyze(cls, content: str, db_path: str | None = None) -> str | None:
        """Analyze content and return rejection reason if it violates protocols."""
        content_lower = content.lower()

        # 1. Static Anti-Pattern Check
        for pattern, reason in cls.ANTI_PATTERNS:
            if re.search(pattern, content_lower):
                ENDOCRINE.pulse(HormoneType.ADRENALINE, 0.4, reason=f"Nemesis Static: {reason}")
                return f"[NEMESIS PROTOCOL ACTIVO] Entropía detectada: {reason}"

        # 2. Dynamic Antibody Check (Delegated to reduce complexity)
        return cls._check_dynamic_antibodies(content_lower, db_path)

    @classmethod
    async def analyze_async(
        cls, content: str, conn: aiosqlite.Connection | None = None
    ) -> str | None:
        """Analyze content asynchronously. Eliminates I/O wait on event loop (Ω₆)."""
        content_lower = content.lower()

        # 1. Static Anti-Pattern Check
        for pattern, reason in cls.ANTI_PATTERNS:
            if re.search(pattern, content_lower):
                ENDOCRINE.pulse(HormoneType.ADRENALINE, 0.4, reason=f"Nemesis Static: {reason}")
                return f"[NEMESIS PROTOCOL ACTIVO] Entropía detectada: {reason}"

        # 2. Dynamic Antibody Check
        for pattern, reason in cls._load_dynamic_antibodies():
            if re.search(pattern, content_lower):
                cls._rejection_history[pattern] = cls._rejection_history.get(pattern, 0) + 1
                count = cls._rejection_history[pattern]

                pulse_val = 0.8 + (min(0.2, count * 0.05))
                ENDOCRINE.pulse(
                    HormoneType.ADRENALINE,
                    pulse_val,
                    reason=f"Nemesis Antibody ({count}x): {reason}",
                )

                if conn:
                    bus = AsyncSignalBus(conn)
                    await bus.emit(
                        "nemesis:rejection",
                        payload={"reason": reason, "vector": pattern, "count": count},
                        source="nemesis-protocol",
                        project="system",
                    )

                if count > 5:
                    logger.critical("💀 [NEMESIS] Metabolic loop detected on vector: %s", pattern)
                    ENDOCRINE.pulse(HormoneType.CORTISOL, 0.4, reason="Metabolic loop Stress")

                return f"[NEMESIS: REJECTED {count}x] Antibody: {reason}"
        return None

    @classmethod
    def _check_dynamic_antibodies(cls, content_lower: str, db_path: str | None) -> str | None:
        """Helper to scan for dynamically generated antibodies."""
        for pattern, reason in cls._load_dynamic_antibodies():
            if re.search(pattern, content_lower):
                # Ω₃: Metabolic Loop Prevention
                cls._rejection_history[pattern] = cls._rejection_history.get(pattern, 0) + 1
                count = cls._rejection_history[pattern]

                pulse_val = 0.8 + (min(0.2, count * 0.05))  # Punishment climbs
                ENDOCRINE.pulse(
                    HormoneType.ADRENALINE,
                    pulse_val,
                    reason=f"Nemesis Antibody ({count}x): {reason}",
                )

                # Ω₅: Emit signal if db_path is available
                if db_path:
                    cls._emit_rejection_signal(db_path, pattern, reason, count)

                if count > 5:
                    logger.critical("💀 [NEMESIS] Metabolic loop detected on vector: %s", pattern)
                    ENDOCRINE.pulse(HormoneType.CORTISOL, 0.4, reason="Metabolic loop Stress")

                return f"[NEMESIS: REJECTED {count}x] Antibody: {reason}"
        return None

    @classmethod
    def _emit_rejection_signal(cls, db_path: str, pattern: str, reason: str, count: int) -> None:
        """Emits a signal to the CORTEX bus about the rejection."""
        try:
            with db_connect(db_path) as conn:
                bus = SignalBus(conn)
                bus.emit(
                    "nemesis:rejection",
                    payload={"reason": reason, "vector": pattern, "count": count},
                    source="nemesis-protocol",
                    project="system",
                )
        except Exception as e:  # noqa: BLE001 — signal emission failure should not crash analysis
            logger.debug("Failed to emit nemesis signal: %s", e)

    @classmethod
    def assimilate(cls, vector: str, reason: str, db_path: str | None = None) -> bool:
        """
        Ω₅: Dynamic Immunity. Converts an attack vector into a permanent antibody.
        'Asimilar el ataque y convertirlo en anticuerpo antes de que llegue al núcleo.'
        """
        if any(v == vector for v, _ in cls.ANTI_PATTERNS) or any(
            v == vector for v, _ in cls._load_dynamic_antibodies()
        ):
            return False  # Already assimilated

        logger.warning("🦾 [IMMUNITAS] Assimilating attack vector: %s", vector)
        cls.append_antibody(vector, f"Dynamic Immunity: {reason}")

        # Hormonal surge for systemic mobilization
        ENDOCRINE.pulse(HormoneType.ADRENALINE, 0.6, reason="Immuno-assimilation")
        ENDOCRINE.pulse(HormoneType.NEURAL_GROWTH, 0.2, reason="Structural Adaptation")

        if db_path:
            try:
                with db_connect(db_path) as conn:
                    bus = SignalBus(conn)
                    bus.emit(
                        "nemesis:assimilation",
                        payload={"vector": vector, "reason": reason},
                        source="nemesis-protocol",
                        project="system",
                    )
            except Exception as e:  # noqa: BLE001 — must not crash analysis
                logger.debug("Failed to emit assimilation signal: %s", e)

        return True

    @classmethod
    def append_antibody(cls, vector: str, antibody: str) -> None:
        """Appends a new antibody to the nemesis.md ledger."""
        date_str = datetime.date.today().isoformat()
        new_row = f"| `{vector}` | {antibody} | {date_str} |\n"

        try:
            with open(cls.NEMESIS_PATH, "a") as f:
                f.write(new_row)
        except OSError as e:
            # Ω₅: survive at all costs — log but do not crash.
            logger.error("Error appending antibody to nemesis.md: %s", e)
