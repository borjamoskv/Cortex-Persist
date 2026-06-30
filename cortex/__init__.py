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


def _map_name(fullname: str) -> str:
    if fullname.startswith("cortex_extensions"):
        return "babylon60.extensions" + fullname[len("cortex_extensions"):]
    elif fullname.startswith("cortex"):
        return "babylon60" + fullname[len("cortex"):]
    return fullname


_in_ensure_compat = False


def _ensure_compat_aliases():
    global _in_ensure_compat
    if _in_ensure_compat:
        return
    _in_ensure_compat = True
    try:
        for name in list(sys.modules.keys()):
            if name.startswith("babylon60.") or name == "babylon60":
                if name.startswith("babylon60.extensions"):
                    alias1 = "cortex_extensions" + name[len("babylon60.extensions"):]
                elif name.startswith("babylon60"):
                    alias1 = "cortex" + name[len("babylon60"):]
                else:
                    alias1 = name

                if alias1 not in sys.modules:
                    sys.modules[alias1] = _CortexCompat(alias1)

                if name.startswith("babylon60"):
                    alias2 = "cortex" + name[len("babylon60"):]
                    if alias2 not in sys.modules:
                        sys.modules[alias2] = _CortexCompat(alias2)
    finally:
        _in_ensure_compat = False


class _CortexCompat(types.ModuleType):
    """Minimal proxy that redirects cortex.X attribute access to babylon60.X."""

    def __init__(self, name: str):
        super().__init__(name)
        target_pkg = _map_name(name)
        self.__package__ = target_pkg
        self.__name__ = name
        self.__file__ = None
        self.__path__ = None

        # Set __spec__ to prevent ValueError on find_spec
        try:
            if target_pkg in sys.modules and hasattr(sys.modules[target_pkg], "__spec__"):
                self.__spec__ = sys.modules[target_pkg].__spec__
            else:
                from importlib.machinery import ModuleSpec
                self.__spec__ = ModuleSpec(name, loader=None)
        except Exception:
            self.__spec__ = None

        try:
            if target_pkg in sys.modules:
                target_mod = sys.modules[target_pkg]
                if hasattr(target_mod, "__file__"):
                    self.__file__ = target_mod.__file__
                if hasattr(target_mod, "__path__"):
                    self.__path__ = target_mod.__path__
        except Exception:
            pass

    @property
    def _real_module(self):
        target_pkg = _map_name(self.__name__)
        return importlib.import_module(target_pkg)

    def __getattr__(self, name):
        # Do not delegate module identity dunders to the target module
        if name in {"__name__", "__spec__", "__loader__", "__package__"}:
            if name in self.__dict__:
                return self.__dict__[name]
            raise AttributeError(f"module '{self.__name__}' has no attribute '{name}'")

        # Short-circuit other dunders to prevent recursion and slow import lookups
        if name.startswith("__") and name.endswith("__"):
            if name in self.__dict__:
                return self.__dict__[name]
            target_pkg = _map_name(self.__name__)
            try:
                mod = importlib.import_module(target_pkg)
                if hasattr(mod, name):
                    return getattr(mod, name)
            except Exception:
                pass
            raise AttributeError(f"module '{self.__name__}' has no attribute '{name}'")

        target_pkg = _map_name(self.__name__)
        sub_target = f"{target_pkg}.{name}"
        try:
            sub_mod = importlib.import_module(sub_target)
            proxy = _CortexCompat(f"{self.__name__}.{name}")
            sys.modules[proxy.__name__] = proxy
            setattr(self, name, proxy)
            return proxy
        except ImportError:
            mod = importlib.import_module(target_pkg)
            if hasattr(mod, name):
                val = getattr(mod, name)
                return val
            raise AttributeError(
                f"module '{self.__name__}' has no attribute '{name}' "
                f"({target_pkg}.{name} not found)"
            )

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        target_pkg = _map_name(self.__name__)
        try:
            mod = importlib.import_module(target_pkg)
            setattr(mod, name, value)
        except Exception:
            pass

    def __delattr__(self, name):
        try:
            super().__delattr__(name)
        except AttributeError:
            pass
        target_pkg = _map_name(self.__name__)
        try:
            mod = importlib.import_module(target_pkg)
            if hasattr(mod, name):
                delattr(mod, name)
        except Exception:
            pass


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
    """Meta path finder that redirects cortex.* and cortex_extensions.* to babylon60.*."""

    def find_spec(self, fullname, path, target=None):
        if fullname in ("cortex", "cortex_extensions") or fullname.startswith(("cortex.", "cortex_extensions.")):
            target_name = _map_name(fullname)
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
        return _CortexCompat(spec.name)

    def exec_module(self, module):
        pass

    def find_module(self, fullname, path=None):
        if fullname in ("cortex", "cortex_extensions") or fullname.startswith(("cortex.", "cortex_extensions.")):
            return self
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
        target = _map_name(fullname)
        mod = importlib.import_module(target)
        sys.modules[fullname] = mod
        return mod


if not any(isinstance(f, _CortexFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _CortexFinder())
