"""Silicio-Reconfigurable-Logic (SRL) (P1): Runtime Logic Recompilation.

Permite el hot-swapping de lógica de negocio sin interrupción de servicio.
"""

from __future__ import annotations

import importlib
import sys
import logging
from typing import Any, Callable, Dict

logger = logging.getLogger("cortex.engine.srl")

class SRLRegistry:
    """Registro de lógica reconfigurable (Hot-Swapping)."""

    def __init__(self):
        self.logic_map: Dict[str, Callable] = {}
        self.versions: Dict[str, int] = {}

    def register(self, name: str, func: Callable):
        """Registra una función lógica."""
        self.logic_map[name] = func
        self.versions[name] = self.versions.get(name, 0) + 1
        logger.info("⚡ [SRL] Lógica registrada: %s (v%d)", name, self.versions[name])

    def execute(self, name: str, *args, **kwargs) -> Any:
        """Ejecuta la lógica actual."""
        if name not in self.logic_map:
            raise ValueError(f"Lógica '{name}' no encontrada en el registro SRL.")
        return self.logic_map[name](*args, **kwargs)

    def hot_swap(self, name: str, module_path: str, function_name: str):
        """Recarga la lógica desde un módulo externo en caliente."""
        try:
            if module_path in sys.modules:
                importlib.reload(sys.modules[module_path])
            module = importlib.import_module(module_path)
            new_func = getattr(module, function_name)
            self.register(name, new_func)
            logger.info("🔥 [SRL] Hot-Swap exitoso para: %s", name)
        except Exception as e:
            logger.error("❌ [SRL] Fallo en Hot-Swap para %s: %s", name, str(e))
            raise

if __name__ == "__main__":
    def legacy_logic(x): return x * 2
    
    registry = SRLRegistry()
    registry.register("pricing", legacy_logic)
    print(f"Legacy result: {registry.execute('pricing', 10)}")
    
    # En runtime, podríamos redefinir y registrar de nuevo
    def new_logic(x): return x * 3
    registry.register("pricing", new_logic)
    print(f"New result: {registry.execute('pricing', 10)}")
