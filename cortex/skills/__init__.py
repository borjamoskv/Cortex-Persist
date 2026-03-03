# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX Skills Module — Cognitive Graph Engine.

De un directorio de .md a un grafo cognitivo vivo.
Skills que se registran solos, declaran capacidades y se componen bajo demanda.
"""

from cortex.skills.registry import SkillManifest, SkillRegistry
from cortex.skills.router import SkillRouter
from cortex.skills.synthesis_omega import SynthesisOmega, trigger_synthesis

__all__ = [
    "SkillManifest",
    "SkillRegistry",
    "SkillRouter",
    "SynthesisOmega",
    "trigger_synthesis",
]
