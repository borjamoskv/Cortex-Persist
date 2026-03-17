# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX Skills Module — Cognitive Graph Engine.

De un directorio de .md a un grafo cognitivo vivo.
Skills que se registran solos, declaran capacidades y se componen bajo demanda.
"""

from cortex.extensions.skills.registry import SkillManifest, SkillRegistry
from cortex.extensions.skills.router import SkillRouter

__all__ = [
    "SkillManifest",
    "SkillRegistry",
    "SkillRouter",
]
