"""
CORTEX — The Sovereign Ledger for AI Agents.

Local-first memory infrastructure with vector search, temporal facts,
and cryptographic vaults. Zero network dependencies.
"""

import sys

try:
    # Use pysqlite3 if available (allows newer SQLite versions + extensions)
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

__version__ = "0.3.0b1"
__author__ = "Borja Moskv"

# Lazy imports — CortexEngine and experimental modules load on first access
_LAZY_IMPORTS = {
    "CortexEngine": "cortex.engine",
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


__all__ = ["CortexEngine", "__version__"]
