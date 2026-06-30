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

    def __getattr__(self, name):
        target_pkg = _map_name(self.__name__)
        sub_target = f"{target_pkg}.{name}"
        try:
            sub_mod = importlib.import_module(sub_target)
            proxy = _CortexCompat(f"{self.__name__}.{name}")
            sys.modules[proxy.__name__] = proxy
            setattr(self, name, proxy)
            _ensure_compat_aliases()
            return proxy
        except ImportError:
            mod = importlib.import_module(target_pkg)
            if hasattr(mod, name):
                val = getattr(mod, name)
                _ensure_compat_aliases()
                return val
            raise AttributeError(
                f"module '{self.__name__}' has no attribute '{name}' "
                f"({target_pkg}.{name} not found)"
            )

    def __delattr__(self, name):
        try:
            super().__delattr__(name)
        except AttributeError:
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
