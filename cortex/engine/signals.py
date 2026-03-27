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


def log_motor(msg: str, action: str = "PULSE"):
    """Logical/Deterministic engine event (Ω₁)."""
    logger_motor.info("[%s] %s", action, msg)


def log_limbic(msg: str, source: str = "CORE"):
    """Emotional/Stochastic agent pulse (Ω₃)."""
    logger_limbic.info("[%s] %s", source, msg)


def log_bio(msg: str, signal: str = "CIRCA"):
    """Circadian/Hormonal state (Ω₄)."""
    logger_bio.info("[%s] %s", signal, msg)


def log_trust(msg: str, detail: str = "MERKLE"):
    """Trust/Ledger verification (Ω₆)."""
    logger_trust.info("[%s] %s", detail, msg)


def log_autonomic(msg: str, check: str = "TETHER"):
    """Boundary/Survival limits (Ω₀)."""
    logger_autonomic.info("[%s] %s", check, msg)
