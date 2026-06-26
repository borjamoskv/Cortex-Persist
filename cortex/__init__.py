# [C5-REAL] Exergy-Maximized
"""
CORTEX - The Sovereign Ledger for AI Agents.

Local-first memory infrastructure with vector search, temporal facts,
and cryptographic vaults. Zero network dependencies.
"""

import sys
import importlib
import importlib.abc
import importlib.util

class AliasLoader(importlib.abc.Loader):
    def __init__(self, target_module):
        self.target_module = target_module
    def create_module(self, spec):
        return self.target_module
    def exec_module(self, module):
        pass

class CortexExtensionsRedirector(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == "cortex_extensions" or fullname.startswith("cortex_extensions."):
            target_name = fullname.replace("cortex_extensions", "cortex.extensions", 1)
            try:
                mod = importlib.import_module(target_name)
                spec = importlib.util.spec_from_loader(fullname, AliasLoader(mod), origin=getattr(mod, "__file__", None))
                return spec
            except ImportError:
                return None
        return None

sys.meta_path.insert(0, CortexExtensionsRedirector())

try:
    # Use pysqlite3 if available (allows newer SQLite versions + extensions)
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    import logging


__version__ = "1.0.0"
__author__ = "by borjamoskv.com"

# Lazy imports - CortexEngine and experimental modules load on first access
_LAZY_IMPORTS = {
    "CortexEngine": "cortex.engine",
    "api": "cortex.api",
    "routes": "cortex.routes",
}

_EXPERIMENTAL_MODULES = (
    "autopoiesis",
    "circadian_cycle",
    "digital_endocrine",
    "epigenetic_memory",
    "strategic_disobedience",
    "zero_prompting",
)


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        import importlib

        mod = importlib.import_module(_LAZY_IMPORTS[name])
        attr = getattr(mod, name)
        globals()[name] = attr  # Cache for subsequent access
        return attr
    if name in _EXPERIMENTAL_MODULES:
        try:
            import importlib

            mod = importlib.import_module(f"cortex.experimental.{name}")
            globals()[name] = mod
            return mod
        except ImportError as err:
            raise AttributeError(f"module 'cortex' has no attribute {name!r}") from err
    raise AttributeError(f"module 'cortex' has no attribute {name!r}")


__all__ = ["CortexEngine", "__version__", "api", "routes"]  # pyright: ignore[reportUnsupportedDunderAll]
