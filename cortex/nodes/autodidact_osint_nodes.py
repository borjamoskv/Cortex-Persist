#!/usr/bin/env python3
"""
cortex/nodes/autodidact_osint_nodes.py
═══════════════════════════════════════════════════════════════
AUTODIDACT OSINT: Extracción y Evasión
Motor de inyección en el DAG epistémico C5-REAL (Cortex-Persist)
═══════════════════════════════════════════════════════════════
Protocolo: C5-REAL | R8 Mitosis | Causal Vector: OSINT_ENGINE
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class OsintBlock(Enum):
    LEGAL_FRAMEWORK = "C1"
    METADATA_EXTRACTION = "C2"
    EVASION_ARCHITECTURE = "C3"

@dataclass
class AutodidactOsintNode:
    id: str
    index: int
    name: str
    block: OsintBlock
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    verification_method: str = "Empirical evasion & legal audit"
    validation_status: str = "PARTIAL_TRUNCATED"
    hash: str = ""
    injected_at: str = ""

    def compute_hash(self) -> str:
        payload = f"{self.id}|{self.name}|{self.block.value}|{','.join(sorted(self.dependencies))}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def __post_init__(self):
        self.hash = self.compute_hash()
        if not self.injected_at:
            self.injected_at = datetime.now(timezone.utc).isoformat()

def build_core_osint_nodes() -> list[AutodidactOsintNode]:
    """
    Inyecta las primitivas core desde la sesión AUTODIDACT.
    """
    return [
        AutodidactOsintNode(
            id="OSINT-001", index=1, name="Triple Test (Legitimate Interest)",
            block=OsintBlock.LEGAL_FRAMEWORK,
            description="El scraping requiere justificar propósito, necesidad y balancear derechos (CNIL)."
        ),
        AutodidactOsintNode(
            id="OSINT-002", index=2, name="LSSI B2B Sanction Mapping",
            block=OsintBlock.LEGAL_FRAMEWORK,
            description="Cold emailing automatizado de correos extraídos vía OSINT vulnera LSSI. Sancionable por AEPD."
        ),
        AutodidactOsintNode(
            id="OSINT-003", index=3, name="EXIF GPS Extraction (WSTG-INFO-05)",
            block=OsintBlock.METADATA_EXTRACTION,
            description="IFD 0x8825. Requiere Pillow get_ifd(). Ajuste vectorial hemisférico ineludible (S/W = -1)."
        ),
        AutodidactOsintNode(
            id="OSINT-004", index=4, name="Dynamic User-Agent Spoofing",
            block=OsintBlock.EVASION_ARCHITECTURE,
            description="Rotación ponderada (65% Chrome, 20% FF) con reconstrucción total de Headers para eludir WAF heurístico."
        ),
        AutodidactOsintNode(
            id="OSINT-005", index=5, name="Topological Obfuscation",
            block=OsintBlock.EVASION_ARCHITECTURE,
            description="Mallas de proxies dinámicos para evitar Rate Limiting. (Payload truncated)."
        )
    ]

def inject_to_cortex():
    nodes = build_core_osint_nodes()
    for n in nodes:
        print(f"[C5-REAL] Inyectada Primitiva OSINT: {n.id} -> {n.name} [{n.hash}]")

if __name__ == "__main__":
    inject_to_cortex()
