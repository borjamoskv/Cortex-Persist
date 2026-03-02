import importlib.abc
import importlib.machinery
import sys
from typing import Final


class ThermodynamicViolationError(Exception):
    """
    KETER-OMEGA EXCEPTION: La asimetría técnica ha sido violada.
    Terminación instantánea para proteger el Cold Node.
    """


class CyanideImportHook(importlib.abc.MetaPathFinder):
    """
    Guardián de importación. Si se detecta un intento de cargar una
    librería de red o parseo de APIs, lanza envenenamiento y mata el proceso.
    """

    _POISONED_MODULES: Final[set[str]] = {
        "requests",
        "aiohttp",
        "urllib3",
        "httpx",
        "socket",
        "http.client",
        "cortex.moltbook",  # Añadir red
    }

    def find_spec(self, fullname: str, path, target=None):
        base_module = fullname.split(".")[0]
        # Si el prefijo exacto matcha molbook
        if fullname.startswith("cortex.moltbook") or base_module in self._POISONED_MODULES:
            print("🔥 THERMODYNAMIC BORDER COLLAPSE 🔥")
            print(f"FATAL: Attempted to import '{fullname}' within Cold Mode.")
            print("Activating Cyanide Protocol. Self-destructing.")
            raise ThermodynamicViolationError(1)

        return None  # Continúa con el loader normal si es seguro


class ThermodynamicBorder:
    _sealed: bool = False

    @classmethod
    def seal(cls) -> None:
        """
        Bloquea herméticamente el entorno. Cualquier importación
        de red subsecuente matará el proceso. O(1) comprobación por import.
        """
        if cls._sealed:
            return

        sys.meta_path.insert(0, CyanideImportHook())
        cls._sealed = True
