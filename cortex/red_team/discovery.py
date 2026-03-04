"""
CORTEX v6.0 — DiscoveryProvider (Ω₁: Multi-Scale Causality).

Motor soberano de reconocimiento para el Red Team Swarm.
Escanea el sistema en busca de superficies de ataque y genera
payloads de entrada basados en la introspección del AST y firmas.

Axioma Ω₁: Toda causa es alcanzable si escaneas a la escala correcta.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import types
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("cortex.red_team.discovery")


class DiscoveryProvider:
    """
    Sovereign Reconnaissance Engine.

    Descubre objetivos candidatos (clases y funciones) dentro del namespace
    de CORTEX para que el Red Team Swarm inyecte caos.
    """

    # Namespaces críticos que deben ser asediados por defecto
    CRITICAL_NAMESPACES = [
        "cortex.memory.manager",
        "cortex.memory.working",
        "cortex.engine.forgetting_oracle",
        "cortex.storage.router",
        "cortex.database.cache",
    ]

    def __init__(self, target_namespaces: list[str] | None = None) -> None:
        self.namespaces = target_namespaces or self.CRITICAL_NAMESPACES
        self._cache: list[tuple[str, Callable, dict[str, Any]]] = []

    def discover(self) -> list[tuple[str, Callable, dict[str, Any]]]:
        """
        Escanea los namespaces y devuelve una lista de tripletes (service, func, seed).
        """
        logger.info("🔭 [DISCOVERY] Initiating system reconnaissance...")
        targets = []

        for ns in self.namespaces:
            try:
                module = importlib.import_module(ns)
                module_targets = self._scan_module(ns, module)
                targets.extend(module_targets)
            except ImportError as e:
                logger.error("❌ [DISCOVERY] Failed to import namespace %s: %s", ns, e)
                continue

        logger.info(
            "🔭 [DISCOVERY] Found %d attack surfaces across %d namespaces.",
            len(targets),
            len(self.namespaces),
        )
        self._cache = targets
        return targets

    def _scan_module(
        self, ns_name: str, module: types.ModuleType
    ) -> list[tuple[str, Callable, dict[str, Any]]]:
        """Extrae funciones y métodos públicos del módulo."""
        surfaces = []

        # 1. Escanear clases (ej. CortexMemoryManager)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != ns_name:
                continue
            if name.startswith("_"):
                continue

            for func_name, func_obj in inspect.getmembers(
                obj, lambda x: inspect.isfunction(x) or inspect.ismethod(x)
            ):
                if func_name.startswith("_"):
                    continue
                # Saltar estáticos por ahora
                if "self" not in inspect.signature(func_obj).parameters:
                    continue

                seed = self._generate_seed_inputs(func_obj)
                if seed is not None:
                    # Envoltorio para instanciación (esto es complejo: el Red Team
                    # debería usar instancias reales si el engine las tiene,
                    # o intentar instanciar con mocks).
                    surfaces.append((f"{ns_name}.{name}", func_obj, seed))

        # 2. Escanear funciones a nivel de módulo
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if obj.__module__ != ns_name:
                continue
            if name.startswith("_"):
                continue

            seed = self._generate_seed_inputs(obj)
            if seed is not None:
                surfaces.append((ns_name, obj, seed))

        return surfaces

    def _generate_seed_inputs(self, func: Callable) -> dict[str, Any] | None:
        """
        Intenta generar un diccionario de inputs válidos (seed) basado en type hints.
        Si no hay suficientes datos para una semilla válida, devuelve None.
        """
        sig = inspect.signature(func)
        params = sig.parameters
        seed = {}

        for name, param in params.items():
            if name == "self" or name == "cls":
                continue

            # Si tiene valor por defecto, lo usamos como semilla
            if param.default is not inspect.Parameter.empty:
                seed[name] = param.default
                continue

            # Mapeo básico de tipos para semillas
            if isinstance(param.annotation, type) and issubclass(param.annotation, str):
                seed[name] = "seed_data"
            elif isinstance(param.annotation, type) and issubclass(param.annotation, int):
                seed[name] = 1
            elif isinstance(param.annotation, type) and issubclass(param.annotation, float):
                seed[name] = 1.0
            elif isinstance(param.annotation, type) and issubclass(param.annotation, bool):
                seed[name] = True
            elif isinstance(param.annotation, type) and issubclass(param.annotation, dict):
                seed[name] = {"key": "val"}
            elif isinstance(param.annotation, type) and issubclass(param.annotation, list):
                seed[name] = ["val"]
            else:
                # Si es un tipo complejo sin default, no podemos generar una semilla segura
                seed[name] = "byzantine_placeholder"

        # Si el 100% de los parámetros tienen semilla (o son opcionales), es un candidato.
        return seed
