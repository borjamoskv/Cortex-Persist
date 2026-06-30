"""Backward compatibility shim — cortex.X redirects to babylon60.X.

This module exists solely for backward compatibility with external consumers
that may still import from the 'cortex' namespace. All canonical code lives
in babylon60/.

Usage:
    from cortex.engine import CortexEngine  # redirects to babylon60.engine
    from babylon60.engine import CortexEngine  # canonical
"""
import importlib
import importlib.util
import sys
import types
from importlib.machinery import ModuleSpec


def _map_name(fullname: str) -> str:
    if fullname.startswith("cortex_extensions"):
        return "babylon60.extensions" + fullname[len("cortex_extensions"):]
    elif fullname.startswith("cortex"):
        return "babylon60" + fullname[len("cortex"):]
    return fullname


class _CortexCompat(types.ModuleType):
    """Transparent proxy that redirects cortex.X attribute access to babylon60.X."""

    def __init__(self, name: str, spec: ModuleSpec = None):
        super().__init__(name)
        self.__name__ = name
        target_pkg = _map_name(name)
        self.__package__ = target_pkg
        
        if spec is not None:
            self.__spec__ = spec
        else:
            try:
                target_spec = importlib.util.find_spec(target_pkg)
                self.__spec__ = target_spec if target_spec else ModuleSpec(name, loader=None)
            except Exception:
                self.__spec__ = ModuleSpec(name, loader=None)
                
        try:
            target_mod = importlib.import_module(target_pkg)
            self.__file__ = getattr(target_mod, "__file__", None)
            self.__path__ = getattr(target_mod, "__path__", None)
        except Exception:
            pass

    def __getattr__(self, name):
        # Shield module identity dunders
        if name in {"__name__", "__spec__", "__loader__", "__package__"}:
            raise AttributeError(f"module '{self.__name__}' has no attribute '{name}'")

        target_pkg = _map_name(self.__name__)

        # 1. Resolve attribute from the real module
        try:
            mod = importlib.import_module(target_pkg)
            if hasattr(mod, name):
                return getattr(mod, name)
        except Exception:
            pass

        # 2. Submodule resolution via proxy namespace
        try:
            sub_cortex = f"{self.__name__}.{name}"
            return importlib.import_module(sub_cortex)
        except ImportError:
            pass

        raise AttributeError(f"module '{self.__name__}' has no attribute '{name}'")

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        # Mirror state to the canonical module
        if name not in {"__name__", "__spec__", "__loader__", "__package__", "__file__", "__path__"}:
            try:
                mod = importlib.import_module(_map_name(self.__name__))
                setattr(mod, name, value)
            except Exception:
                pass

    def __delattr__(self, name):
        try:
            super().__delattr__(name)
        except AttributeError:
            pass
        # Mirror deletion to the canonical module
        if name not in {"__name__", "__spec__", "__loader__", "__package__", "__file__", "__path__"}:
            try:
                mod = importlib.import_module(_map_name(self.__name__))
                if hasattr(mod, name):
                    delattr(mod, name)
            except Exception:
                pass


class _CortexFinder:
    """Meta path finder (PEP 451) redirecting cortex.* imports to babylon60.*."""

    def find_spec(self, fullname, path, target=None):
        if fullname in ("cortex", "cortex_extensions") or fullname.startswith(("cortex.", "cortex_extensions.")):
            target_name = _map_name(fullname)
            try:
                if importlib.util.find_spec(target_name) is not None:
                    return ModuleSpec(fullname, self)
            except Exception:
                pass
        return None

    def create_module(self, spec):
        return _CortexCompat(spec.name, spec=spec)

    def exec_module(self, module):
        target_name = _map_name(module.__name__)
        try:
            real_mod = importlib.import_module(target_name)
            for k, v in real_mod.__dict__.items():
                if k not in {"__name__", "__spec__", "__loader__", "__package__", "__file__", "__path__"}:
                    setattr(module, k, v)
        except Exception:
            pass


# Bootstrap the top-level module proxy
import babylon60 as babylon60  # noqa: E402

_compat = _CortexCompat(__name__)
_compat.__path__ = getattr(sys.modules[__name__], "__path__", [])
_compat.__file__ = getattr(sys.modules[__name__], "__file__", None)
sys.modules[__name__] = _compat

if not any(isinstance(f, _CortexFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _CortexFinder())
