"""Backward compatibility shim — cortex.X redirects to babylon60.X.

This module exists solely for backward compatibility with external consumers
that may still import from the 'cortex' namespace. All canonical code lives
in babylon60/.

Usage:
    from cortex.engine import CortexEngine  # redirects to babylon60.engine
    from babylon60.engine import CortexEngine  # canonical
"""
import importlib
import sys
import types


class _CortexCompat(types.ModuleType):
    """Minimal proxy that redirects cortex.X attribute access to babylon60.X."""

    def __getattr__(self, name):
        try:
            return importlib.import_module(f"babylon60.{name}")
        except ImportError:
            if hasattr(babylon60, name):
                return getattr(babylon60, name)
            raise AttributeError(
                f"module 'cortex' has no attribute '{name}' "
                f"(babylon60.{name} not found)"
            )


# Install the compatibility redirect
import babylon60 as babylon60  # noqa: E402

_compat = _CortexCompat(__name__)
_compat.__path__ = [__path__[0]] if "__path__" in dir() else []
_compat.__file__ = __file__
_compat.__package__ = __name__

# Register so `from cortex.X import Y` works
sys.modules[__name__] = _compat


# Also install a meta_path finder for deep submodule imports
class _CortexFinder:
    """Meta path finder that redirects cortex.* to babylon60.*."""

    def find_spec(self, fullname, path, target=None):
        if fullname == "cortex" or fullname.startswith("cortex."):
            target_name = fullname.replace("cortex", "babylon60", 1)
            try:
                # Only return a spec if it is actually a module or package, not an attribute
                import importlib.util
                if importlib.util.find_spec(target_name) is not None:
                    from importlib.machinery import ModuleSpec
                    return ModuleSpec(fullname, self)
            except Exception:
                pass
        return None

    def create_module(self, spec):
        target = spec.name.replace("cortex", "babylon60", 1)
        return importlib.import_module(target)

    def exec_module(self, module):
        pass

    def find_module(self, fullname, path=None):
        if fullname == "cortex" or fullname.startswith("cortex."):
            return self
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
        target = fullname.replace("cortex", "babylon60", 1)
        mod = importlib.import_module(target)
        sys.modules[fullname] = mod
        return mod


if not any(isinstance(f, _CortexFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _CortexFinder())
