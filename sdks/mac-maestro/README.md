# mac-maestro

Semantic-first macOS GUI automation with safety gates and structured traces.

## Why

Pixel bots are brittle. `mac-maestro` matches native macOS UI semantically via accessibility snapshots.

## Features

- Semantic matching by role/title/value
- Safety policy for destructive actions
- Structured JSON traces
- Backend abstraction for testing
- Native-app automation oriented

## Install

```bash
pip install mac-maestro
```

## Example

```python
from mac_maestro import MacMaestro, ClickAction
from mac_maestro.backends.mock import MockBackend
from mac_maestro.models import AXNodeSnapshot

root = AXNodeSnapshot(
    element_id="root",
    role="AXWindow",
    title="Main",
    children=[
        AXNodeSnapshot(element_id="save_btn", role="AXButton", title="Save")
    ],
)

maestro = MacMaestro(
    bundle_id="com.example.app",
    backend=MockBackend(root=root),
)

trace = maestro.run([
    ClickAction(role="AXButton", title="Save")
])

print(trace.to_json())
```
