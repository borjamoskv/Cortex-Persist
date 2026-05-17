from cortex.cli.main import _discover_command_modules
import importlib
import sys

modules = _discover_command_modules()
for m in modules:
    print(f"Importing {m}...", flush=True)
    try:
        importlib.import_module(f"cortex.cli.{m}")
        print(f"Done {m}", flush=True)
    except Exception as e:
        print(f"Failed {m}: {e}", flush=True)
print("Finished loading")
