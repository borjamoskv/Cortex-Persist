# [C5-REAL] Exergy-Maximized
import logging
import os
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class CognitivePrimitive(BaseModel):
    id: int
    name: str
    algebraic_topology: str
    description: str
    base60_constant: int = 0

class LatticeworkStore:
    """
    [C5-REAL] O(1) in-memory epistemic foundation for the 100 Primitives of Cognitive Exergy.
    Serves as the truth-source for the LatticeworkDaemon's thermodynamic interventions.
    """
    def __init__(self):
        self.primitives: dict[int, CognitivePrimitive] = {}
        self._initialize_core_primitives()

    def _initialize_core_primitives(self):
        # Localizamos el archivo de mapeo estructural (C5-REAL Bridge)
        root_path = Path(__file__).parent.parent.parent
        mapping_path = root_path / "AUTODIDACT_SYSTEMS_EXERGY_MAPPING.md"
        
        if not mapping_path.exists():
            mapping_path = Path(os.getcwd()) / "AUTODIDACT_SYSTEMS_EXERGY_MAPPING.md"
            if not mapping_path.exists():
                logger.warning(f"[LatticeworkStore] No se encontró el manifiesto de exergía en {mapping_path}")
                return

        try:
            with open(mapping_path, encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"[LatticeworkStore] Error al leer el manifiesto: {e}")
            return

        current_id: int | None = None
        current_name: str | None = None
        current_topology: str | None = None
        current_desc: str | None = None

        def save_current():
            nonlocal current_id, current_name, current_topology, current_desc
            if current_id is not None and current_name is not None:
                topo = current_topology or "TBD"
                desc = current_desc or "TBD"
                b60_const = abs(hash(topo)) % 3600
                self.primitives[current_id] = CognitivePrimitive(
                    id=current_id,
                    name=current_name,
                    algebraic_topology=topo,
                    description=desc,
                    base60_constant=b60_const
                )
            # Reset
            current_id = None
            current_name = None
            current_topology = None
            current_desc = None

        for line in lines:
            line_str = line.strip()
            if line_str.startswith("### "):
                save_current()
                match = re.match(r"^###\s*(\d+)\.\s*(.*)", line_str)
                if match:
                    current_id = int(match.group(1))
                    current_name = match.group(2).strip()
            elif current_id is not None:
                if "**Topología Algebraica:**" in line_str:
                    parts = line_str.split("**Topología Algebraica:**", 1)
                    topo = parts[1].strip()
                    for delim in ["\\[", "\\]", "\\(", "\\)", "`", "[", "]"]:
                        topo = topo.replace(delim, "")
                    current_topology = topo.strip()
                elif "**Mapping C5-REAL" in line_str or "**Isomorfismo Causal:**" in line_str:
                    parts = line_str.split(":", 1)
                    if len(parts) > 1:
                        current_desc = parts[1].strip()
                    else:
                        current_desc = line_str

        # Guardar el último
        save_current()

    def get_primitive(self, pid: int) -> Optional[CognitivePrimitive]:
        return self.primitives.get(pid)

    def search_by_keyword(self, text: str) -> list[CognitivePrimitive]:
        text_lower = text.lower()
        return [
            p for p in self.primitives.values()
            if text_lower in p.name.lower() or text_lower in p.description.lower()
        ]
