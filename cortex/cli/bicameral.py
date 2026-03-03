"""
CORTEX V4 Bicameral Console (Subconscious Interface)

Separates the Sovereign Agent's monologue into Limbic, Motor, and Autonomic streams.
"""

import json
import os
import time
from typing import Any

from rich.console import Console
from rich.theme import Theme

# Industrial Noir 2026 Theme
bicameral_theme = Theme(
    {
        "limbic": "dim magenta",  # Reflejando memoria, intuición, cicatrices
        "motor": "bold cyan",  # Ejecución pura, frío, metálico
        "autonomic": "bold red",  # Peligro, límites, tether
        "trust": "bold yellow",  # Consenso, Merkle, Ledger
        "bio": "bold green",  # Ciclo circadiano, Hormonas digitales
        "limbic_prefix": "magenta",
        "motor_prefix": "cyan",
        "autonomic_prefix": "red",
        "trust_prefix": "yellow",
        "bio_prefix": "green",
    }
)

console = Console(theme=bicameral_theme)


class BicameralConsole:
    """The Subconscious Interface separating agent internal monologue."""

    def _relay_event(
        self,
        stream: str,
        source: str,
        message: str,
        meta: dict[str, Any] = None,  # type: ignore[reportArgumentType]
    ) -> None:
        """Relays the event to an external listener (Notch Alcove)."""
        event = {
            "stream": stream,
            "source": source,
            "message": message,
            "timestamp": str(int(time.time())),
            "meta": meta or {},
        }
        # In this initial implementation, we append to a dedicated relay buffer file.
        relay_path = os.path.expanduser("~/.cortex/relay_buffer.jsonl")
        try:
            with open(relay_path, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            pass  # Fail silently to avoid interrupting the agent loop

    def log_limbic(self, message: str, source: str = "LORE") -> None:
        """Logs emotional, historical, or allergy-driven reasoning."""
        prefix = f"[limbic_prefix][▶ CORTEX Límbico | {source.upper():<7}][/limbic_prefix]"
        console.print(f"{prefix} [limbic]{message}[/limbic]")
        self._relay_event("limbic", source, message)

    def log_motor(self, message: str, action: str = "EXEC") -> None:
        """Logs fast execution and physical interaction."""
        prefix = f"[motor_prefix][▶ CORTEX Motor   | {action.upper():<7}][/motor_prefix]"
        console.print(f"{prefix} [motor]{message}[/motor]")
        self._relay_event("motor", action, message)

    def log_autonomic(self, message: str, check: str = "TETHER") -> None:
        """Logs hard boundaries, resource checks, and autolysis."""
        prefix = f"[autonomic_prefix][⚠ CORTEX T.C.A   | {check.upper():<7}][/autonomic_prefix]"
        console.print(f"{prefix} [autonomic]{message}[/autonomic]")
        self._relay_event("autonomic", check, message)

    def log_trust(self, message: str, detail: str = "MERKLE") -> None:
        """Logs cryptographic verification and consensus voting."""
        prefix = f"[trust_prefix][🛡 CORTEX Trust  | {detail.upper():<7}][/trust_prefix]"
        console.print(f"{prefix} [trust]{message}[/trust]")
        self._relay_event("trust", detail, message)

    def log_bio(self, message: str, signal: str = "CIRCA") -> None:
        """Logs biological system status, hormones, and circadian phases."""
        from cortex.engine.endocrine import ENDOCRINE

        balance = ENDOCRINE.balance
        cortisol = balance.get("CORTISOL", 0)
        growth = balance.get("NEURAL_GROWTH", 0)

        levels = f"[C:{cortisol:.2f} G:{growth:.2f}]"
        prefix = f"[bio_prefix][🧬 CORTEX Bio    | {signal.upper():<7}][/bio_prefix]"
        console.print(f"{prefix} {levels} [bio]{message}[/bio]")

        self._relay_event(
            "bio", signal, message, meta={"cortisol": cortisol, "neural_growth": growth}
        )

    def log_entropy(self, message: str, scan: str = "DECALC") -> None:
        """Logs thermodynamic decay of certainty (Protocol Ω₃-E)."""
        prefix = f"[trust_prefix][🧬 CORTEX Doubt  | {scan.upper():<7}][/trust_prefix]"
        console.print(f"{prefix} [trust]{message}[/trust]")
        self._relay_event("trust", f"DOUBT_{scan}", message)


bicameral = BicameralConsole()
