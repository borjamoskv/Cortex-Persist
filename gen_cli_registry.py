import importlib
import json

from cortex.cli.common import cli
from cortex.cli.main import _discover_command_modules

registry = {}
failed = {}

modules = _discover_command_modules()

for module_name in modules:
    cli.commands.clear()
    full_name = f"cortex.cli.{module_name}"
    try:
        importlib.import_module(full_name)
        for cmd_name in cli.commands.keys():
            if cmd_name in registry:
                pass  # conflict, last one wins or we can log it
            registry[cmd_name] = full_name
    except Exception as err:
        failed[module_name] = str(err)

with open("cortex/cli/_registry.json", "w") as f:
    json.dump({"commands": registry, "failed": failed}, f, indent=2)

print(f"Generated registry with {len(registry)} commands.")
