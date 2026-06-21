# [C5-REAL] Exergy-Maximized
"""
CORTEX VSA Engine Adapter - C5-REAL
Exposes the sovereign VSAEngine from the skills directory.
"""

import sys
from pathlib import Path

# Resolve skill directory from repository root first, then fall back to home directory
_SKILL_DIR_LOCAL = Path(__file__).resolve().parent.parent / "skills" / "vsa-sdm-memory-omega"
_SKILL_DIR_HOME = Path.home() / ".gemini" / "antigravity" / "skills" / "vsa-sdm-memory-omega"

for skill_dir in (_SKILL_DIR_LOCAL, _SKILL_DIR_HOME):
    if skill_dir.exists() and str(skill_dir) not in sys.path:
        sys.path.insert(0, str(skill_dir))

try:
    from vsa_engine import VSAEngine  # pyright: ignore[reportAssignmentType]
except ImportError:
    # Fallback dummy class if the skill engine is not available, avoiding crash-on-import
    class VSAEngine:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "VSAEngine could not be imported from local or home skills directory."
            )
