# [C5-REAL] Exergy-Maximized
"""CLI bootstrap with tolerant command-module loading.

This keeps the root CLI usable even when some subcommand modules are
temporarily broken by unresolved merge conflicts elsewhere in the tree.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

from babylon60.cli.common import cli

logger = logging.getLogger(__name__)

_COMMAND_MODULE_SUFFIX = "_cmds"
_COMMAND_DIR = Path(__file__).parent
_LEGACY_COMMAND_MODULES = ("crud", "ledger", "purge", "slow_tip", "vote_ledger")


def _discover_command_modules() -> list[str]:
    modules: set[str] = set()
    for module_info in pkgutil.iter_modules([str(_COMMAND_DIR)]):
        if module_info.ispkg:
            continue
        if module_info.name.endswith(_COMMAND_MODULE_SUFFIX):
            modules.add(module_info.name)

    for module_name in _LEGACY_COMMAND_MODULES:
        if (_COMMAND_DIR / f"{module_name}.py").exists():
            modules.add(module_name)

    return sorted(modules)


def _load_command_modules() -> tuple[list[str], dict[str, str]]:
    loaded: list[str] = []
    failed: dict[str, str] = {}

    for module_name in _discover_command_modules():
        full_name = f"babylon60.cli.{module_name}"
        try:
            importlib.import_module(full_name)
            loaded.append(module_name)
        except Exception as err:
            failed[module_name] = f"{type(err).__name__}: {err}"
            logger.debug("Skipping CLI module %s: %s", full_name, err)

    return loaded, failed


LOADED_COMMAND_MODULES, FAILED_COMMAND_MODULES = _load_command_modules()
cli.loaded_command_modules = tuple(LOADED_COMMAND_MODULES)  # type: ignore[attr-defined]
cli.failed_command_modules = dict(FAILED_COMMAND_MODULES)  # type: ignore[attr-defined]

__all__ = ["FAILED_COMMAND_MODULES", "LOADED_COMMAND_MODULES", "cli"]
