# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import os
import sys
import importlib
import importlib.abc
import importlib.util


import types

class ProxyModule(types.ModuleType):
    def __init__(self, name, real_module):
        super().__init__(name)
        object.__setattr__(self, '_real_module', real_module)

    def __getattribute__(self, name):
        if name in ('_real_module', '__class__', '__spec__', '__loader__', '__path__', '__file__', '__name__'):
            return object.__getattribute__(self, name)
        
        try:
            val = object.__getattribute__(self, name)
            if isinstance(val, types.ModuleType):
                return val
        except AttributeError:
            pass

        if name == '__dict__':
            try:
                real = object.__getattribute__(self, '_real_module')
            except AttributeError:
                return object.__getattribute__(self, '__dict__')
            d = dict(real.__dict__)
            d.update({
                '__name__': object.__getattribute__(self, '__name__'),
            })
            try:
                d['__spec__'] = object.__getattribute__(self, '__spec__')
            except AttributeError:
                pass
            try:
                d['__loader__'] = object.__getattribute__(self, '__loader__')
            except AttributeError:
                pass
            if hasattr(self, '__path__'):
                d['__path__'] = object.__getattribute__(self, '__path__')
            if hasattr(self, '__file__'):
                d['__file__'] = object.__getattribute__(self, '__file__')
            return d
            
        return getattr(self._real_module, name)

    def __setattr__(self, name, value):
        if name in ('_real_module', '__spec__', '__loader__', '__path__', '__file__', '__name__'):
            object.__setattr__(self, name, value)
        elif isinstance(value, types.ModuleType):
            object.__setattr__(self, name, value)
        else:
            setattr(self._real_module, name, value)

    def __dir__(self):
        return dir(self._real_module)


class LazyAliasLoader(importlib.abc.Loader):
    def __init__(self, target_name):
        self.target_name = target_name

    def create_module(self, spec):
        real_module = importlib.import_module(self.target_name)
        proxy = ProxyModule(spec.name, real_module)
        if hasattr(real_module, '__path__'):
            proxy.__path__ = real_module.__path__
        if hasattr(real_module, '__file__'):
            proxy.__file__ = real_module.__file__
        return proxy

    def exec_module(self, module):
        pass


import threading
if not hasattr(sys, '_cortex_babylon_local'):
    sys._cortex_babylon_local = threading.local()


class CortexExtensionsRedirector(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if getattr(sys._cortex_babylon_local, 'guard', False):
            return None
            
        if fullname == "cortex_extensions" or fullname.startswith("cortex_extensions."):
            target_name = fullname.replace("cortex_extensions", "cortex.extensions", 1)
            sys._cortex_babylon_local.guard = True
            try:
                spec = importlib.util.find_spec(target_name)
                if spec is not None:
                    return importlib.util.spec_from_loader(
                        fullname, LazyAliasLoader(target_name), origin=spec.origin
                    )
            except Exception:
                return None
            finally:
                sys._cortex_babylon_local.guard = False
        
        # Redirect legacy cortex submodules to physical babylon60 locations
        for prefix in ("cortex.api", "cortex.crypto", "cortex.guards", "cortex.ledger", "cortex.engine", "cortex.audit"):
            if fullname == prefix or fullname.startswith(prefix + "."):
                target_name = fullname.replace("cortex", "babylon60", 1)
                sys._cortex_babylon_local.guard = True
                try:
                    spec = importlib.util.find_spec(target_name)
                    if spec is not None:
                        return importlib.util.spec_from_loader(
                            fullname, LazyAliasLoader(target_name), origin=spec.origin
                        )
                except Exception:
                    return None
                finally:
                    sys._cortex_babylon_local.guard = False
        return None


sys.meta_path.insert(0, CortexExtensionsRedirector())
import os
if os.environ.get("CORTEX_SHADOW_MODE"):
    from babylon60.shadow_tracer import enable_tracer
    enable_tracer(mode=os.environ.get("CORTEX_SHADOW_MODE"))

from pathlib import Path

# Set environment variables for tests globally before any imports/fixtures run
os.environ["CORTEX_TESTING"] = "1"
os.environ["CORTEX_NO_OMEGA"] = "1"
os.environ["CORTEX_MASTER_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"
os.environ["CORTEX_VIRGO_MODE"] = "TEST"
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import pytest
import sqlite3

@pytest.fixture(autouse=True)
def default_testing_env(monkeypatch):
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "1")
    monkeypatch.setenv("CORTEX_NO_EMBED", "1")
    monkeypatch.setenv("CORTEX_MASTER_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")

_raw_sqlite3_connect = sqlite3.connect


def _test_safe_sqlite3_connect(*args, **kwargs):
    """Enforce WAL and busy_timeout in tests to prevent flaky lock errors."""
    conn = _raw_sqlite3_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.Error:
        pass
    return conn


sqlite3.connect = _test_safe_sqlite3_connect

# ── Repo-local import resolution ──────────────────────────────────────────────
# Several legacy tests import modules that live outside the installed package
# surface. Resolve them relative to the checkout so CI doesn't depend on a
# developer-specific home directory layout.
_REPO_ROOT = Path(__file__).resolve().parents[1]
for extra_path in (
    _REPO_ROOT,
    _REPO_ROOT / "cortex-core",
    _REPO_ROOT / "scripts" / "sortu",
):
    if extra_path.exists() and str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))


@pytest.fixture(autouse=True)
def mock_local_embedder(monkeypatch):
    """Mock the local embedder to prevent 10s ONNX model loads during every test."""

    class DummyEmbedder:
        def embed(self, content: str | list[str]) -> list[float] | list[list[float]]:
            if isinstance(content, str):
                return [0.0] * 384
            return [[0.0] * 384 for _ in content]

        async def aembed(self, content: str | list[str]) -> list[float] | list[list[float]]:
            if isinstance(content, str):
                return [0.0] * 384
            return [[0.0] * 384 for _ in content]

    from cortex.engine import CortexEngine

    monkeypatch.setattr(CortexEngine, "_get_embedder", lambda self: DummyEmbedder())


@pytest.fixture(autouse=True)
def reset_anomaly_detector():
    """Reset the anomaly detector before each test to prevent bulk mutation blocks."""
    from cortex.extensions.security.anomaly_detector import DETECTOR

    DETECTOR.reset()


@pytest.fixture(autouse=True)
def inject_test_master_key(monkeypatch):
    """Ensure a deterministic Master Key is available for tests."""
    monkeypatch.setenv("CORTEX_TESTING", "1")
    monkeypatch.setenv("CORTEX_NO_OMEGA", "1")
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "1")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test")
    # Base64 for 32 bytes of '0'
    monkeypatch.setenv("CORTEX_MASTER_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")


@pytest.fixture(autouse=True)
def isolate_swarm_ledger(tmp_path, monkeypatch):
    """Ensure each test gets an isolated SwarmLedger database and KeyManager files."""
    db_path = tmp_path / "swarm_ledger.db"
    monkeypatch.setenv("CORTEX_SWARM_DB_PATH", str(db_path))
    monkeypatch.setenv("CORTEX_DB_PATH", str(tmp_path))


def pytest_configure(config):
    """Optimize pytest collection and execution on macOS."""
    import gc
    import sys
    import warnings

    sys.settrace(None)
    sys.setprofile(None)
    gc.freeze()
    warnings.filterwarnings("ignore", category=pytest.PytestUnhandledThreadExceptionWarning)


def pytest_sessionfinish(session, exitstatus):
    """Save exit status before finalization."""
    session.config.exitstatus = exitstatus
    
    # Export shadow tracer graph if enabled
    import os
    shadow_mode = os.environ.get("CORTEX_SHADOW_MODE")
    if shadow_mode:
        try:
            from babylon60.shadow_tracer import _global_tracer
            if _global_tracer:
                filename = f"compatibility_delta_graph_{shadow_mode}.json"
                _global_tracer.export_compatibility_graph(filename)
                sys.stdout.write(f"\n[C5-REAL] Compatibility delta graph exported to {filename}\n")
                sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"\n[ERROR] Failed to export shadow graph: {e}\n")
            sys.stderr.flush()


def pytest_unconfigure(config):
    """Force exit to prevent finalization hangs on leaked daemon threads."""
    if hasattr(config, "workerinput"):
        return
    import os
    import sys

    sys.stdout.flush()
    sys.stderr.flush()
    exitstatus = getattr(config, "exitstatus", 0)
    os._exit(exitstatus)
