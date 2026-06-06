# [C5-REAL] Exergy-Maximized
import ast
from pathlib import Path

source_file = Path("cortex/sica/colony.py")
target_dir = Path("cortex/sica/colony_module")

source_code = source_file.read_text()
tree = ast.parse(source_code)

classes = {}
for node in tree.body:
    if isinstance(node, ast.ClassDef):
        # Extract the source code for the class
        start_line = node.lineno - 1
        end_line = node.end_lineno
        classes[node.name] = "\n".join(source_code.splitlines()[start_line:end_line])

types_code = f"""from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any

{classes.get("GeneFragment", "")}

{classes.get("TournamentResult", "")}

{classes.get("AgentSpecialization", "")}
"""

genetics_code = f"""from __future__ import annotations
import copy
import logging
import random
from dataclasses import dataclass, field
from typing import Any
from collections import defaultdict
from cortex.sica.strategy import SICAStrategy, GenomicHeuristics

from .types import GeneFragment

logger = logging.getLogger("cortex.sica.colony.genetics")

{classes.get("GenePool", "")}

{classes.get("GenomeCrossover", "")}
"""

tournament_code = f"""from __future__ import annotations
import logging
import random
from typing import Any

from .types import GeneFragment, TournamentResult
from .genetics import GenePool

logger = logging.getLogger("cortex.sica.colony.tournament")

{classes.get("Tournament", "")}
"""

specialization_code = f"""from __future__ import annotations
import logging
from collections import Counter
from typing import Any

from .types import AgentSpecialization

logger = logging.getLogger("cortex.sica.colony.specialization")

{classes.get("SpecializationDetector", "")}
"""

core_code = f"""from __future__ import annotations
import logging
from typing import Any

from cortex.sica.strategy import SICAStrategy

from .types import GeneFragment, AgentSpecialization
from .genetics import GenePool, GenomeCrossover
from .tournament import Tournament
from .specialization import SpecializationDetector

logger = logging.getLogger("cortex.sica.colony.core")

{classes.get("Colony", "")}
"""

init_code = """from .types import GeneFragment, TournamentResult, AgentSpecialization
from .genetics import GenePool, GenomeCrossover
from .tournament import Tournament
from .specialization import SpecializationDetector
from .core import Colony

__all__ = [
    "GeneFragment",
    "TournamentResult",
    "AgentSpecialization",
    "GenePool",
    "GenomeCrossover",
    "Tournament",
    "SpecializationDetector",
    "Colony",
]
"""

target_dir.mkdir(exist_ok=True, parents=True)
(target_dir / "types.py").write_text(types_code)
(target_dir / "genetics.py").write_text(genetics_code)
(target_dir / "tournament.py").write_text(tournament_code)
(target_dir / "specialization.py").write_text(specialization_code)
(target_dir / "core.py").write_text(core_code)
(target_dir / "__init__.py").write_text(init_code)

print("Split colony.py into cortex/sica/colony_module/")
