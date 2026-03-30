"""
CORTEX V6 - Engine Logging Infrastructure.
Ω-Signal purification.
"""

import logging

# Modular Loggers (Ω₁)
logger_motor = logging.getLogger("cortex.engine.motor")
logger_limbic = logging.getLogger("cortex.engine.limbic")
logger_bio = logging.getLogger("cortex.engine.bio")
logger_trust = logging.getLogger("cortex.engine.trust")
logger_autonomic = logging.getLogger("cortex.engine.autonomic")


def wrap_terminal(msg: str, vibe: str | None = None) -> str:
    """Wraps a message in a terminal-friendly CSS class."""
    if vibe:
        return f'<span class="{vibe}">{msg}</span>'
    return msg


def log_motor(msg: str, action: str = "PULSE", vibe: str | None = None):
    """Logical/Deterministic engine event (Ω₁)."""
    logger_motor.info("[%s] %s", action, wrap_terminal(msg, vibe))


def log_limbic(msg: str, source: str = "CORE", vibe: str | None = None):
    """Emotional/Stochastic agent pulse (Ω₃)."""
    logger_limbic.info("[%s] %s", source, wrap_terminal(msg, vibe))


def log_bio(msg: str, signal: str = "CIRCA", vibe: str | None = None):
    """Circadian/Hormonal state (Ω₄)."""
    logger_bio.info("[%s] %s", signal, wrap_terminal(msg, vibe))


def log_trust(msg: str, detail: str = "MERKLE", vibe: str | None = None):
    """Trust/Ledger verification (Ω₆)."""
    logger_trust.info("[%s] %s", detail, wrap_terminal(msg, vibe))


def log_autonomic(msg: str, check: str = "TETHER", vibe: str | None = None):
    """Boundary/Survival limits (Ω₀)."""
    logger_autonomic.info("[%s] %s", check, wrap_terminal(msg, vibe))
