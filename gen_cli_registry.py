import json
from cortex.cli.main import cli, FAILED_COMMAND_MODULES

registry = {}
for cmd_name, cmd in cli.commands.items():
    if hasattr(cmd, "callback") and cmd.callback:
        registry[cmd_name] = cmd.callback.__module__
    else:
        # If it's a group or command without callback
        registry[cmd_name] = "cortex.cli"

with open("cortex/cli/_registry.json", "w") as f:
    json.dump({"commands": registry, "failed": FAILED_COMMAND_MODULES}, f, indent=2)

print(f"Generated registry with {len(registry)} commands.")
