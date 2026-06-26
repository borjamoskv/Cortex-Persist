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

from cortex.cli.common import cli

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
        full_name = f"cortex.cli.{module_name}"
        try:
            importlib.import_module(full_name)
            loaded.append(module_name)
        except Exception as err:
            failed[module_name] = f"{type(err).__name__}: {err}"
            logger.debug("Skipping CLI module %s: %s", full_name, err)

    return loaded, failed


_loaded = False
LOADED_COMMAND_MODULES: list[str] = []
FAILED_COMMAND_MODULES: dict[str, str] = {}


def _ensure_loaded() -> None:
    global _loaded, LOADED_COMMAND_MODULES, FAILED_COMMAND_MODULES
    if not _loaded:
        _loaded = True
        loaded, failed = _load_command_modules()
        LOADED_COMMAND_MODULES.extend(loaded)
        FAILED_COMMAND_MODULES.update(failed)
        cli.loaded_command_modules = tuple(LOADED_COMMAND_MODULES)  # type: ignore[attr-defined]
        cli.failed_command_modules = dict(FAILED_COMMAND_MODULES)  # type: ignore[attr-defined]


# Override Click's list_commands and get_command dynamically to defer importing modules.
original_list_commands = cli.list_commands
original_get_command = cli.get_command

def lazy_list_commands(ctx: click.Context) -> list[str]:
    _ensure_loaded()
    return original_list_commands(ctx)

def lazy_get_command(ctx: click.Context, name: str) -> click.Command | None:
    _ensure_loaded()
    return original_get_command(ctx, name)

cli.list_commands = lazy_list_commands
cli.get_command = lazy_get_command

__all__ = ["FAILED_COMMAND_MODULES", "LOADED_COMMAND_MODULES", "cli"]
