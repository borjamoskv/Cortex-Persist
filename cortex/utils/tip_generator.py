# SOVEREIGN TIP generator – cada tip está anclado a una ley física.

"""Utility module to generate tips that reference concrete physical laws.

The system’s design principle (Ω₂ – Entropic Asymmetry) states that every
unnecessary bit of information increases entropy and thus energy consumption.
These tips make that principle explicit for developers, linking software
clean‑up actions to well‑known physical laws (Landauer, Thermodynamics, etc.).
"""

from random import choice

# Tuple of (law name, description linking the law to software hygiene)
_PHYSICS_TIPS = [
    (
        "Ley de Landauer",
        "Eliminar datos temporales reduce la disipación de calor asociada a cada bit borrado."
    ),
    (
        "Segunda Ley de la Termodinámica",
        "Reducir logs redundantes disminuye la entropía del sistema, ahorrando energía de I/O."
    ),
    (
        "Principio de Conservación de la Energía",
        "Cada proceso extra consume energía; eliminar código muerto reduce el consumo total."
    ),
    (
        "Principio de Ockham",
        "Menos variables y funciones disminuyen la complejidad cognitiva y el coste computacional."
    ),
    (
        "Ley de Maxwell (Demonio)",
        "Un algoritmo que elimina ruido actúa como un demonio que reduce la entropía del registro."
    ),
]


def random_physical_tip() -> str:
    """Return a formatted tip anchored to a physical law.

    The tip is returned ready to be inserted into markdown documents, e.g.:
    ````markdown
    💡 **[SOVEREIGN TIP]** *Ley de Landauer:* Eliminar datos temporales ...
    ````
    """
    law, desc = choice(_PHYSICS_TIPS)
    return f"💡 **[SOVEREIGN TIP]** *{law}:* {desc}"
