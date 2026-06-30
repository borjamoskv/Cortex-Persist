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
_LEGACY_COMMAND_MODULES = (
    "crud",
    "ledger",
    "purge",
    "slow_tip",
    "vote_ledger",
    "apoptosis",
    "telemetry",
)


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


class LazyCommandsDict(dict):
    """A dictionary that lazily triggers command module loading on access."""

    def __init__(self, loader) -> None:
        self._loader = loader
        super().__init__()

    def __bool__(self) -> bool:
        return True

    def _trigger(self) -> None:
        self._loader()

    def __getitem__(self, key):
        self._trigger()
        return super().__getitem__(key)

    def __len__(self) -> int:
        self._trigger()
        return super().__len__()

    def __contains__(self, key) -> bool:
        self._trigger()
        return super().__contains__(key)

    def __iter__(self):
        self._trigger()
        return super().__iter__()

    def keys(self):
        self._trigger()
        return super().keys()

    def values(self):
        self._trigger()
        return super().values()

    def items(self):
        self._trigger()
        return super().items()

    def get(self, key, default=None):
        self._trigger()
        return super().get(key, default)


# Preserve any commands already registered, then replace with lazy loader.
existing_commands = cli.commands
if type(existing_commands).__name__ != "LazyCommandsDict":
    cli.commands = LazyCommandsDict(_ensure_loaded)
    if existing_commands:
        cli.commands.update(existing_commands)

__all__ = ["FAILED_COMMAND_MODULES", "LOADED_COMMAND_MODULES", "cli"]
