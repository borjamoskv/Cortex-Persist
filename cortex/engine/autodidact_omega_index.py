# [C5-REAL] Exergy-Maximized — Autodidact-Ω Engine v5.0
# Author: Borja Moskv (borjamoskv)
"""
AUTODIDACT-Ω UNIFIED INDEX
===========================
Fusión de dos manifiestos ortogonales en un único grafo ejecutable:
  - AUTODIDACT_SYSTEMS_EXERGY_MAPPING.md   → Topología Algebraica [1..100]
  - AUTODIDACT_C5_REAL_PRIMITIVES.md       → Primitivas Ejecutables [C5-REAL-001..100]

El resultado es el `UnifiedPrimitiveNode`: un nodo ejecutable con:
  - algebraic_topology: str (ecuación LaTeX)
  - c5_real_id: str         (e.g. "C5-REAL-031")
  - kernel_constant: str    (e.g. "AST_DIRECT_INJECT")
  - description: str
  - base60_constant: int    (derivado del hash de la topología)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("cortex.autodidact.omega")


@dataclass(frozen=True)
class SystemExergyNode:
    """Nodo extraído de AUTODIDACT_SYSTEMS_EXERGY_MAPPING.md"""
    id: int
    name: str
    algebraic_topology: str
    c5_real_mapping: str   # e.g. "C5-EMERGENT_SYNTHESIS"
    description: str


@dataclass(frozen=True)
class C5RealPrimitive:
    """Nodo extraído de AUTODIDACT_C5_REAL_PRIMITIVES.md"""
    id: int                 # 1..100
    c5_real_id: str         # "C5-REAL-031"
    kernel_constant: str    # "AST_DIRECT_INJECT"
    description: str
    section: str


@dataclass(frozen=True)
class UnifiedPrimitiveNode:
    """
    Nodo unificado C5-REAL: cruza la Topología Algebraica con la Primitiva Ejecutable.
    Este es el átomo del Latticework Motor.
    """
    id: int
    name: str
    algebraic_topology: str
    c5_real_mapping: str       # del mapping.md
    c5_real_id: str            # del primitives.md
    kernel_constant: str       # del primitives.md
    description: str
    section: str
    base60_constant: int       # hash % 3600


class AutodidactOmegaIndex:
    """
    [C5-REAL] Autodidact-Ω Unified Index.

    Carga los dos manifiestos y los funde en un grafo O(1) de 100 UnifiedPrimitiveNodes.
    Este es el índice maestro sobre el que opera el LatticeworkDaemon.
    """

    def __init__(self, repo_root: Path | None = None):
        self._root = repo_root or Path(__file__).parent.parent.parent
        self._exergy_nodes: dict[int, SystemExergyNode] = {}
        self._c5_primitives: dict[int, C5RealPrimitive] = {}
        self.index: dict[int, UnifiedPrimitiveNode] = {}
        self._load_all()

    # ── Loaders ────────────────────────────────────────────────────────────────

    def _load_exergy_mapping(self) -> None:
        path = self._root / "AUTODIDACT_SYSTEMS_EXERGY_MAPPING.md"
        if not path.exists():
            logger.error("[AutodidactΩ] AUTODIDACT_SYSTEMS_EXERGY_MAPPING.md not found at %s", path)
            return

        content = path.read_text(encoding="utf-8")

        # Match blocks: ### N. Name\n  * **Topología Algebraica:** `...`  (or LaTeX \[...\])
        # then  * **Mapping C5-REAL (`C5-KEY`):** description
        block_pattern = re.compile(
            r"### (\d+)\.\s+(.+?)\n"          # id + name
            r".*?Topología Algebraica:\*\*\s*"
            r"(?:`([^`]+)`|\\\[(.+?)\\\])"    # backtick OR \[...\]
            r".*?Mapping C5-REAL \(`([^`]+)`\):\s*\**\s*(.+?)(?=\n### |\n---|\Z)",
            re.DOTALL | re.IGNORECASE,
        )

        for m in block_pattern.finditer(content):
            nid      = int(m.group(1))
            name     = m.group(2).strip()
            alg_bt   = m.group(3)   # backtick form
            alg_ltx  = m.group(4)   # LaTeX form
            algebra  = (alg_bt or alg_ltx or "").strip()
            c5_map   = m.group(5).strip()
            desc     = re.sub(r"\s+", " ", m.group(6)).strip()

            self._exergy_nodes[nid] = SystemExergyNode(
                id=nid,
                name=name,
                algebraic_topology=algebra,
                c5_real_mapping=c5_map,
                description=desc,
            )

        logger.info("[AutodidactΩ] Exergy Mapping loaded: %d nodes", len(self._exergy_nodes))

    def _load_c5_primitives(self) -> None:
        path = self._root / "AUTODIDACT_C5_REAL_PRIMITIVES.md"
        if not path.exists():
            logger.error("[AutodidactΩ] AUTODIDACT_C5_REAL_PRIMITIVES.md not found at %s", path)
            return

        content = path.read_text(encoding="utf-8")

        current_section = "Unknown"
        section_re = re.compile(r"^### ([IVXLC]+\.\s+.+)$", re.MULTILINE)
        row_re = re.compile(
            r"\|\s*`(C5-REAL-(\d+))`\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|"
        )

        # Build section start positions
        section_positions: list[tuple[int, str]] = []
        for sm in section_re.finditer(content):
            section_positions.append((sm.start(), sm.group(1).strip()))

        def section_for_pos(pos: int) -> str:
            result = "Unknown"
            for sp, sn in section_positions:
                if sp <= pos:
                    result = sn
                else:
                    break
            return result

        for rm in row_re.finditer(content):
            c5_id   = rm.group(1)           # "C5-REAL-001"
            nid     = int(rm.group(2))       # 1
            const   = rm.group(3).strip()    # "WAL_ATOMIC_LOCK"
            desc    = rm.group(4).strip()    # description text
            section = section_for_pos(rm.start())

            self._c5_primitives[nid] = C5RealPrimitive(
                id=nid,
                c5_real_id=c5_id,
                kernel_constant=const,
                description=desc,
                section=section,
            )

        logger.info("[AutodidactΩ] C5-REAL Primitives loaded: %d primitives", len(self._c5_primitives))

    def _build_unified_index(self) -> None:
        all_ids = set(self._exergy_nodes.keys()) | set(self._c5_primitives.keys())

        for nid in sorted(all_ids):
            exergy = self._exergy_nodes.get(nid)
            c5     = self._c5_primitives.get(nid)

            algebra = exergy.algebraic_topology if exergy else ""
            b60 = abs(hash(algebra)) % 3600

            self.index[nid] = UnifiedPrimitiveNode(
                id=nid,
                name=exergy.name if exergy else (c5.kernel_constant if c5 else f"Node-{nid}"),
                algebraic_topology=algebra,
                c5_real_mapping=exergy.c5_real_mapping if exergy else "",
                c5_real_id=c5.c5_real_id if c5 else "",
                kernel_constant=c5.kernel_constant if c5 else "",
                description=exergy.description if exergy else (c5.description if c5 else ""),
                section=c5.section if c5 else "",
                base60_constant=b60,
            )

        logger.info(
            "[AutodidactΩ] Unified Index crystallized: %d nodes. "
            "Exergy coverage: %d/100, C5-REAL coverage: %d/100",
            len(self.index),
            len(self._exergy_nodes),
            len(self._c5_primitives),
        )

    def _load_all(self) -> None:
        self._load_exergy_mapping()
        self._load_c5_primitives()
        self._build_unified_index()

    # ── Query API ──────────────────────────────────────────────────────────────

    def get(self, nid: int) -> UnifiedPrimitiveNode | None:
        return self.index.get(nid)

    def by_kernel_constant(self, constant: str) -> UnifiedPrimitiveNode | None:
        for node in self.index.values():
            if node.kernel_constant == constant:
                return node
        return None

    def by_c5_mapping(self, mapping: str) -> UnifiedPrimitiveNode | None:
        for node in self.index.values():
            if node.c5_real_mapping == mapping:
                return node
        return None

    def search(self, keyword: str) -> list[UnifiedPrimitiveNode]:
        kw = keyword.lower()
        return [
            n for n in self.index.values()
            if kw in n.name.lower() or kw in n.description.lower() or kw in n.kernel_constant.lower()
        ]

    def coverage_report(self) -> dict[str, int | float]:
        exergy_count = sum(1 for n in self.index.values() if n.algebraic_topology)
        c5_count     = sum(1 for n in self.index.values() if n.c5_real_id)
        unified      = sum(1 for n in self.index.values() if n.algebraic_topology and n.c5_real_id)
        total        = len(self.index)
        return {
            "total": total,
            "exergy_nodes": exergy_count,
            "c5_primitives": c5_count,
            "fully_unified": unified,
            "coverage_pct": round(unified / max(total, 1) * 100, 2),
        }
