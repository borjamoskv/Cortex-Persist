# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import builtins
import importlib
import sys
from contextlib import contextmanager
from unittest.mock import patch

_MISSING = object()


@contextmanager
def _temporarily_reset_modules(*names: str):
    previous = {name: sys.modules.get(name) for name in names}
    parent_attrs: dict[str, tuple[object, str, object]] = {}

    for name in names:
        parent_name, _, child_name = name.rpartition(".")
        if not parent_name:
            continue
        parent = sys.modules.get(parent_name)
        if parent is None:
            continue
        parent_attrs[name] = (parent, child_name, getattr(parent, child_name, _MISSING))
        if hasattr(parent, child_name):
            delattr(parent, child_name)

    for name in names:
        sys.modules.pop(name, None)

    try:
        yield
    finally:
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        for parent, child_name, previous_attr in parent_attrs.values():
            if previous_attr is _MISSING:
                if hasattr(parent, child_name):
                    delattr(parent, child_name)
            else:
                setattr(parent, child_name, previous_attr)


def test_routes_package_import_is_lazy_without_fastapi() -> None:
    package_name = "cortex.routes"
    admin_module = "cortex.routes.admin"
    graph_module = "cortex.routes.graph"
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "fastapi" or name.startswith("fastapi."):
            raise ImportError("blocked optional dependency: fastapi")
        return real_import(name, globals, locals, fromlist, level)

    with _temporarily_reset_modules(package_name, admin_module, graph_module):
        with patch("builtins.__import__", side_effect=guarded_import):
            module = importlib.import_module(package_name)

        assert module.__name__ in (package_name, package_name.replace('cortex', 'cortex'))
        assert admin_module not in sys.modules
        assert graph_module not in sys.modules
        assert callable(module.__getattr__)


def test_routes_submodules_materialize_on_demand() -> None:
    package_name = "cortex.routes"
    admin_module = "cortex.routes.admin"
    graph_module = "cortex.routes.graph"

    with _temporarily_reset_modules(package_name, admin_module, graph_module):
        module = importlib.import_module(package_name)

        assert module.admin.__name__ in (admin_module, admin_module.replace("cortex", "cortex"))
        assert admin_module in sys.modules or admin_module.replace("cortex", "cortex") in sys.modules
        assert graph_module not in sys.modules


def test_ledger_origin_signatures_materialize_on_demand() -> None:
    package_name = "cortex.ledger"
    models_module = "cortex.ledger.models"
    origin_module = "cortex.ledger.origin"
    replay_module = "cortex.ledger.replay"

    with _temporarily_reset_modules(package_name, models_module, origin_module, replay_module):
        module = importlib.import_module(package_name)

        assert origin_module not in sys.modules
        assert replay_module not in sys.modules
        assert module.LedgerEvent.__name__ == "LedgerEvent"
        assert models_module in sys.modules or models_module.replace("cortex", "cortex") in sys.modules
        assert origin_module not in sys.modules
        assert replay_module not in sys.modules
        assert module.OriginKeyRegistry.__name__ == "OriginKeyRegistry"
        assert origin_module in sys.modules or origin_module.replace("cortex", "cortex") in sys.modules
        assert replay_module not in sys.modules
        assert module.ReplayAdmissionPolicy.__name__ == "ReplayAdmissionPolicy"
        assert replay_module in sys.modules or replay_module.replace("cortex", "cortex") in sys.modules


def test_browser_package_import_is_lazy_without_playwright() -> None:
    package_name = "cortex.extensions.browser"
    engine_module = "cortex.extensions.browser.engine"
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "playwright.async_api" or name.startswith("playwright."):
            raise ImportError("blocked optional dependency: playwright")
        return real_import(name, globals, locals, fromlist, level)

    with _temporarily_reset_modules(package_name, engine_module):
        with patch("builtins.__import__", side_effect=guarded_import):
            module = importlib.import_module(package_name)

        assert module.__name__ in (package_name, package_name.replace('cortex', 'cortex'))
        assert engine_module not in sys.modules
        assert callable(module.__getattr__)


def test_gate_package_import_is_lazy() -> None:
    package_name = "cortex.extensions.gate"
    core_module = "cortex.extensions.gate.core"
    errors_module = "cortex.extensions.gate.errors"
    enums_module = "cortex.extensions.gate.enums"

    with _temporarily_reset_modules(package_name, core_module, errors_module, enums_module):
        module = importlib.import_module(package_name)

        assert module.__name__ in (package_name, package_name.replace('cortex', 'cortex'))
        assert core_module not in sys.modules
        assert errors_module not in sys.modules
        assert enums_module not in sys.modules
        assert callable(module.__getattr__)


def test_gate_public_exports_materialize_on_demand() -> None:
    package_name = "cortex.extensions.gate"
    core_module = "cortex.extensions.gate.core"
    errors_module = "cortex.extensions.gate.errors"
    enums_module = "cortex.extensions.gate.enums"

    with _temporarily_reset_modules(package_name, core_module, errors_module, enums_module):
        module = importlib.import_module(package_name)

        assert module.GateExpired.__name__ == "GateExpired"
        assert errors_module in sys.modules or errors_module.replace("cortex", "cortex") in sys.modules
        assert core_module not in sys.modules
        assert module.ActionStatus.__name__ == "ActionStatus"
        assert enums_module in sys.modules or enums_module.replace("cortex", "cortex") in sys.modules


def test_signals_package_import_is_lazy_without_aiosqlite() -> None:
    package_name = "cortex.extensions.signals"
    bus_module = "cortex.extensions.signals.bus"
    models_module = "cortex.extensions.signals.models"
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "aiosqlite" or name.startswith("aiosqlite."):
            raise ImportError("blocked optional dependency: aiosqlite")
        return real_import(name, globals, locals, fromlist, level)

    with _temporarily_reset_modules(package_name, bus_module, models_module):
        with patch("builtins.__import__", side_effect=guarded_import):
            module = importlib.import_module(package_name)

        assert module.__name__ in (package_name, package_name.replace('cortex', 'cortex'))
        assert bus_module not in sys.modules
        assert models_module not in sys.modules
        assert callable(module.__getattr__)


def test_signals_public_exports_materialize_on_demand() -> None:
    package_name = "cortex.extensions.signals"
    bus_module = "cortex.extensions.signals.bus"
    models_module = "cortex.extensions.signals.models"

    with _temporarily_reset_modules(package_name, bus_module, models_module):
        module = importlib.import_module(package_name)

        assert module.Signal.__name__ == "Signal"
        assert models_module in sys.modules or models_module.replace("cortex", "cortex") in sys.modules
        assert bus_module not in sys.modules
        assert module.SignalBus.__name__ == "SignalBus"
        assert bus_module in sys.modules or bus_module.replace("cortex", "cortex") in sys.modules


def test_metering_package_import_is_lazy() -> None:
    package_name = "cortex.extensions.metering"
    quotas_module = "cortex.extensions.metering.quotas"
    tracker_module = "cortex.extensions.metering.tracker"

    with _temporarily_reset_modules(package_name, quotas_module, tracker_module):
        module = importlib.import_module(package_name)

        assert module.__name__ in (package_name, package_name.replace('cortex', 'cortex'))
        assert quotas_module not in sys.modules
        assert tracker_module not in sys.modules
        assert callable(module.__getattr__)


def test_metering_public_exports_materialize_on_demand() -> None:
    package_name = "cortex.extensions.metering"
    quotas_module = "cortex.extensions.metering.quotas"
    tracker_module = "cortex.extensions.metering.tracker"

    with _temporarily_reset_modules(package_name, quotas_module, tracker_module):
        module = importlib.import_module(package_name)

        assert "free" in module.PLAN_QUOTAS
        assert quotas_module in sys.modules or quotas_module.replace("cortex", "cortex") in sys.modules
        assert tracker_module not in sys.modules
        assert module.UsageTracker.__name__ == "UsageTracker"
        assert tracker_module in sys.modules or tracker_module.replace("cortex", "cortex") in sys.modules


def test_search_package_import_is_lazy_without_aiosqlite() -> None:
    package_name = "cortex.search"
    hybrid_module = "cortex.search.hybrid"
    models_module = "cortex.search.models"
    text_module = "cortex.search.text"
    vector_module = "cortex.search.vector"
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "aiosqlite" or name.startswith("aiosqlite."):
            raise ImportError("blocked optional dependency: aiosqlite")
        return real_import(name, globals, locals, fromlist, level)

    with _temporarily_reset_modules(
        package_name,
        hybrid_module,
        models_module,
        text_module,
        vector_module,
    ):
        with patch("builtins.__import__", side_effect=guarded_import):
            module = importlib.import_module(package_name)

        assert module.__name__ in (package_name, package_name.replace('cortex', 'cortex'))
        assert hybrid_module not in sys.modules
        assert models_module not in sys.modules
        assert text_module not in sys.modules
        assert vector_module not in sys.modules
        assert callable(module.__getattr__)


def test_search_public_exports_materialize_on_demand() -> None:
    package_name = "cortex.search"
    causal_gap_module = "cortex.search.causal_gap"
    hybrid_module = "cortex.search.hybrid"
    models_module = "cortex.search.models"

    with _temporarily_reset_modules(
        package_name,
        causal_gap_module,
        hybrid_module,
        models_module,
    ):
        module = importlib.import_module(package_name)

        assert module.SearchResult.__name__ == "SearchResult"
        assert models_module in sys.modules or models_module.replace("cortex", "cortex") in sys.modules
        assert causal_gap_module not in sys.modules
        assert hybrid_module not in sys.modules
        assert module.CausalGap.__name__ == "CausalGap"
        assert causal_gap_module in sys.modules or causal_gap_module.replace("cortex", "cortex") in sys.modules
        assert module.hybrid_search.__name__ == "hybrid_search"
        assert hybrid_module in sys.modules or hybrid_module.replace("cortex", "cortex") in sys.modules


def test_gateway_package_import_is_lazy_without_aiosqlite() -> None:
    package_name = "cortex.gateway"
    router_module = "cortex.gateway.router"
    bus_module = "cortex.extensions.signals.bus"
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "aiosqlite" or name.startswith("aiosqlite."):
            raise ImportError("blocked optional dependency: aiosqlite")
        return real_import(name, globals, locals, fromlist, level)

    with _temporarily_reset_modules(package_name, router_module, bus_module):
        with patch("builtins.__import__", side_effect=guarded_import):
            module = importlib.import_module(package_name)

        assert module.__name__ in (package_name, package_name.replace('cortex', 'cortex'))
        assert router_module not in sys.modules
        assert bus_module not in sys.modules
        assert callable(module.__getattr__)


def test_gateway_adapters_package_import_is_lazy_without_fastapi() -> None:
    package_name = "cortex.gateway.adapters"
    rest_module = "cortex.gateway.adapters.rest"
    telegram_module = "cortex.gateway.adapters.telegram"
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "fastapi" or name.startswith("fastapi."):
            raise ImportError("blocked optional dependency: fastapi")
        return real_import(name, globals, locals, fromlist, level)

    with _temporarily_reset_modules(package_name, rest_module, telegram_module):
        with patch("builtins.__import__", side_effect=guarded_import):
            module = importlib.import_module(package_name)

        assert module.__name__ in (package_name, package_name.replace('cortex', 'cortex'))
        assert rest_module not in sys.modules
        assert telegram_module not in sys.modules
        assert callable(module.__getattr__)


def test_ledger_package_import_is_lazy_without_aiosqlite() -> None:
    package_name = "cortex.ledger"
    core_module = "cortex.ledger.ledger_core"
    models_module = "cortex.ledger.models"
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "aiosqlite" or name.startswith("aiosqlite."):
            raise ImportError("blocked optional dependency: aiosqlite")
        return real_import(name, globals, locals, fromlist, level)

    with _temporarily_reset_modules(package_name, core_module, models_module):
        with patch("builtins.__import__", side_effect=guarded_import):
            module = importlib.import_module(package_name)

        assert module.__name__ in (package_name, package_name.replace('cortex', 'cortex'))
        assert core_module not in sys.modules
        assert models_module not in sys.modules
        assert callable(module.__getattr__)


def test_ledger_public_exports_materialize_on_demand() -> None:
    package_name = "cortex.ledger"
    core_module = "cortex.ledger.ledger_core"
    models_module = "cortex.ledger.models"

    with _temporarily_reset_modules(package_name, core_module, models_module):
        module = importlib.import_module(package_name)

        assert module.LedgerEvent.__name__ == "LedgerEvent"
        assert models_module in sys.modules or models_module.replace("cortex", "cortex") in sys.modules
        assert core_module not in sys.modules
        assert module.ImmutableLedger is module.SovereignLedger
        assert core_module in sys.modules or core_module.replace("cortex", "cortex") in sys.modules


def test_graph_package_import_is_lazy_without_aiosqlite() -> None:
    package_name = "cortex.graph"
    backends_module = "cortex.graph.backends"
    engine_module = "cortex.graph.engine"
    models_module = "cortex.graph.models"
    sqlite_backend_module = "cortex.graph.backends.sqlite"
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "aiosqlite" or name.startswith("aiosqlite."):
            raise ImportError("blocked optional dependency: aiosqlite")
        return real_import(name, globals, locals, fromlist, level)

    with _temporarily_reset_modules(
        package_name,
        backends_module,
        engine_module,
        models_module,
        sqlite_backend_module,
    ):
        with patch("builtins.__import__", side_effect=guarded_import):
            module = importlib.import_module(package_name)

        assert module.__name__ in (package_name, package_name.replace('cortex', 'cortex'))
        assert backends_module not in sys.modules
        assert engine_module not in sys.modules
        assert models_module not in sys.modules
        assert sqlite_backend_module not in sys.modules
        assert callable(module.__getattr__)


def test_sync_package_import_is_lazy_without_crypto_stack() -> None:
    package_name = "cortex.extensions.sync"
    common_module = "cortex.extensions.sync.common"
    write_module = "cortex.extensions.sync.write"
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "cortex.crypto" or name.startswith("cortex.crypto."):
            raise ImportError("blocked optional dependency: cortex.crypto")
        return real_import(name, globals, locals, fromlist, level)

    with _temporarily_reset_modules(package_name, common_module, write_module):
        with patch("builtins.__import__", side_effect=guarded_import):
            module = importlib.import_module(package_name)

        assert module.__name__ in (package_name, package_name.replace('cortex', 'cortex'))
        assert common_module not in sys.modules
        assert write_module not in sys.modules
        assert callable(module.__getattr__)
