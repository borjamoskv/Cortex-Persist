# [C5-REAL] Exergy-Maximized
"""
CORTEX - Funtor Base para Guards (OPT-3).

Define la interfaz estructural de un Guard como una transformación natural.
Todo Guard evalúa un estado (payload) y retorna el mismo estado cristalizado si pasa,
o levanta una GuardViolation si incumple la ontología.
"""

from typing import Any, Protocol, TypeVar

E = TypeVar("E")


class GuardViolation(Exception):
    """
    Excepción fundamental levantada cuando el funtor rechaza el estado propuesto.
    Fallo cerrado por defecto (AP-008 fix).
    """

    pass


class Guard(Protocol[E]):
    """
    Transformación natural que recibe un Ente de tipo E y retorna el mismo Ente E
    si satisface las invariantes. Si no, levanta GuardViolation.
    """

    def evaluate(self, payload: E, **kwargs: Any) -> E:
        """
        Evalúa el payload y retorna el mismo si es válido.

        Raises:
            GuardViolation: Si el payload viola las leyes termodinámicas o estructurales.
        """
        ...
