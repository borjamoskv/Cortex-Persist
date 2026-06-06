# [C5-REAL] Exergy-Maximized
import importlib.util
import importlib.machinery
import pathlib
import sys

# Resolve the path to the compiled Rust extension (macOS uses .dylib, fallback to .so)
_ext_names = ["libcortex_rs.dylib", "libcortex_rs.so", "cortex_rs.dll"]
_base = pathlib.Path(__file__).resolve().parent.parent / "cortex_rs" / "target"
_lib_path = None
for _dir in ["release", "debug"]:
    _root = _base / _dir
    for name in _ext_names:
        candidate = _root / name
        if candidate.is_file():
            _lib_path = candidate
            break
    if _lib_path:
        break

if _lib_path is None:
    raise ImportError(f"Compiled cortex_rs library not found in {_base}")

# Load the compiled extension as a Python module named 'cortex_rs'
loader = importlib.machinery.ExtensionFileLoader("cortex_rs", str(_lib_path))
spec = importlib.util.spec_from_loader("cortex_rs", loader)
module = importlib.util.module_from_spec(spec)  # pyright: ignore[reportArgumentType]
loader.exec_module(module)

# Export symbols to this package's namespace
globals().update(module.__dict__)

# Ensure the directory containing the shared library is on sys.path for any submodule imports
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
