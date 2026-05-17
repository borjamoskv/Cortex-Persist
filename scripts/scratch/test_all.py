import sys
import importlib
import os

files = os.listdir("cortex/cli")
modules = [f[:-3] for f in files if f.endswith("_cmds.py")]

for m in sorted(modules):
    with open("current.txt", "w") as f:
        f.write(m)
    try:
        importlib.import_module(f"cortex.cli.{m}")
    except Exception:
        pass
