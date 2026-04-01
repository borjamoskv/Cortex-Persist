"""Sovereign Darknet (Dead-Internet Inversion).

Motor que invierte el consumo digital: descarga crudos del mundo real,
los asimila vía agentes IA y genera tu red social 100% curada localmente.
"""

from __future__ import annotations

from .agents import DarknetAgent
from .ingestor import DarknetIngestor
from .social_ledger import DarknetLedger

__all__ = ["DarknetAgent", "DarknetIngestor", "DarknetLedger"]
