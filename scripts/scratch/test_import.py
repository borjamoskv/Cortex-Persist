import pkgutil
import importlib
import sys

for m in pkgutil.iter_modules(["cortex/cli"]):
    print(f"Importing {m.name}...")
    sys.stdout.flush()
    try:
        importlib.import_module(f"cortex.cli.{m.name}")
        print(f"Imported {m.name} successfully")
    except Exception as e:
        print(f"Failed to import {m.name}: {e}")
    sys.stdout.flush()
