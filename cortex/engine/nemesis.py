import re
import logging
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.signals.bus import SignalBus
import sqlite3

logger = logging.getLogger("cortex.nemesis")


class NemesisRejection(Exception):
    """Raised when a fact violates the 130/100 standard and is rejected by Nemesis."""

    pass


class NemesisProtocol:
    """Enforces the 130/100 standard on all incoming memory facts."""

    _rejection_history: dict[str, int] = {}  # Vector -> Count (Ω₃ Cellular Memory)

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
            with open(cls.NEMESIS_PATH, "r") as f:
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

        # Check static patterns
        for pattern, reason in cls.ANTI_PATTERNS:
            if re.search(pattern, content_lower):
                ENDOCRINE.pulse(
                    HormoneType.ADRENALINE, 0.4, reason=f"Nemesis Static: {reason}"
                )
                return f"[NEMESIS PROTOCOL ACTIVO] Entropía detectada: {reason}"

        # Check dynamic antibodies
        for pattern, reason in cls._load_dynamic_antibodies():
            if re.search(pattern, content_lower):
                # Ω₃: Metabolic Loop Prevention
                cls._rejection_history[pattern] = cls._rejection_history.get(pattern, 0) + 1
                count = cls._rejection_history[pattern]
                
                pulse_val = 0.8 + (min(0.2, count * 0.05))  # Punishment climbs
                
                ENDOCRINE.pulse(
                    HormoneType.ADRENALINE, 
                    pulse_val, 
                    reason=f"Nemesis Antibody ({count}x): {reason}"
                )
                
                # Ω₅: Emit signal if db_path is available
                if db_path:
                    try:
                        with sqlite3.connect(db_path) as conn:
                            bus = SignalBus(conn)
                            bus.emit(
                                "nemesis:rejection",
                                payload={
                                    "reason": reason, 
                                    "vector": pattern, 
                                    "count": count
                                },
                                source="nemesis-protocol",
                                project="system"
                            )
                    except Exception as e:
                        logger.debug("Failed to emit nemesis signal: %s", e)

                if count > 5:
                    logger.critical("💀 [NEMESIS] Metabolic loop detected on vector: %s", pattern)
                    ENDOCRINE.pulse(HormoneType.CORTISOL, 0.4, reason="Metabolic loop Stress")

                return f"[NEMESIS: REJECTED {count}x] Antibody: {reason}"

        return None

    @classmethod
    def append_antibody(cls, vector: str, antibody: str) -> None:
        """Appends a new antibody to the nemesis.md ledger."""
        import datetime

        date_str = datetime.date.today().isoformat()
        new_row = f"| `{vector}` | {antibody} | {date_str} |\n"

        try:
            with open(cls.NEMESIS_PATH, "a") as f:
                f.write(new_row)
        except Exception as e:
            # Fallback to logger if available
            print(f"Error appending antibody to nemesis.md: {e}")
