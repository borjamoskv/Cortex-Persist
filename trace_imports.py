import builtins
import sys

_real_import = builtins.__import__
def _traced_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == "yaml" or name.startswith("yaml."):
        import traceback
        traceback.print_stack()
        raise ImportError(f"{name} blocked")
    return _real_import(name, globals, locals, fromlist, level)

builtins.__import__ = _traced_import

try:
    from cortex.engine import CortexEngine
except Exception as e:
    import traceback
    traceback.print_exc()
