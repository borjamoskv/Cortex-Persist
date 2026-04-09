from __future__ import annotations

import importlib
import sys


def _reset_public_package():
    package = importlib.import_module("cortex_persist")
    for attr in ("AsyncCortexClient", "CortexClient", "CortexEngine"):
        package.__dict__.pop(attr, None)
    for submodule in ("cortex.api.async_client", "cortex.api.client", "cortex.engine"):
        sys.modules.pop(submodule, None)
    return importlib.reload(package)


def test_cortex_persist_exports_are_lazy() -> None:
    package = _reset_public_package()

    assert "cortex.api.client" not in sys.modules
    assert "cortex.engine" not in sys.modules
    assert package.__version__

    client = package.CortexClient
    engine = package.CortexEngine

    assert client.__name__ == "CortexClient"
    assert engine.__name__ == "CortexEngine"
    assert "cortex.api.client" in sys.modules
    assert "cortex.engine" in sys.modules


def test_cortex_persist_async_client_is_exposed() -> None:
    package = _reset_public_package()

    assert "cortex.api.async_client" not in sys.modules

    client = package.AsyncCortexClient

    assert client.__name__ == "AsyncCortexClient"
    assert "cortex.api.async_client" in sys.modules
