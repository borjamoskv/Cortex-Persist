# [C5-REAL] Exergy-Maximized
"""
Sovereign Import Tracer and Shadow Resolver for BABYLON-60 (Wave 2).
Provides runtime virtualization, dependency tracing, cycle detection under collapse,
and JSON compatibility delta graph export.
"""

import importlib.abc
import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


class _TracerAliasLoader(importlib.abc.Loader):
    def __init__(self, target_module):
        self.target_module = target_module
    def create_module(self, spec):
        return self.target_module
    def exec_module(self, module):
        pass

class ShadowResolver(importlib.abc.MetaPathFinder):
    """
    Wave 2 Shadow Resolver.
    Redirects imports from cortex to babylon60 if a physical replacement exists,
    otherwise tracks the legacy dependency ('would-break-in-wave2') and falls back.
    """
    def __init__(self, tracer):
        self.tracer = tracer

    def find_spec(self, fullname, path, target=None):
        # Prevent recursion when the tracer itself imports modules
        if fullname.startswith("babylon60.shadow_tracer") or fullname == "babylon60.shadow_tracer":
            return None

        # Check if we are intercepting cortex imports
        if fullname == "cortex" or fullname.startswith("cortex."):
            # Determine caller
            caller = self.tracer.get_caller_module()
            
            # Map name to babylon60 space to see if a physical file exists there
            babylon_fullname = fullname.replace("cortex", "babylon60", 1)
            has_replacement = self.tracer.has_physical_module(babylon_fullname)
            
            if has_replacement:
                # Redirect to babylon60 implementation
                self.tracer.log_redirect(fullname, babylon_fullname, caller)
                try:
                    mod = importlib.import_module(babylon_fullname)
                    spec = importlib.util.spec_from_loader(
                        fullname, _TracerAliasLoader(mod), origin=getattr(mod, "__file__", None)
                    )
                    return spec
                except Exception:
                    pass
            else:
                # Log would-break event
                self.tracer.log_would_break(fullname, caller)
        
        # Intercept babylon60 imports if shadow is disabled
        if (fullname == "babylon60" or fullname.startswith("babylon60.")) and self.tracer.mode == "shadow-disabled":
            # In shadow-disabled mode, babylon60 must act completely independent and not alias to cortex.
            # If no physical module exists in babylon60, the import should fail (ModuleNotFoundError)
            if not self.tracer.has_physical_module(fullname):
                raise ModuleNotFoundError(f"No physical module found for '{fullname}' in shadow-disabled mode")

        return None

class ImportTracer:
    """
    Tracks import dependency relationships, detects cycles under alias collapse,
    and generates the compatibility delta graph.
    """
    def __init__(self, mode="present"):
        # Mode can be: "present", "shadow-disabled", "redirected"
        self.mode = mode
        self.imports = defaultdict(set)  # importer -> set of imported
        self.redirects = []  # list of dicts: {source, target, caller}
        self.would_breaks = []  # list of dicts: {source, caller}
        self.physical_cache = {}
        self.project_root = Path(__file__).resolve().parents[1]
        self._installed = False
        self._resolver = None
        self.ledger = None

    def get_caller_module(self):
        """Finds the name of the first user module up the stack."""
        try:
            # Walk up the call stack to find the first module outside importlib/builtins
            frame = sys._getframe(1)
            while frame:
                name = frame.f_globals.get("__name__")
                if name and name not in ("importlib._bootstrap", "importlib._bootstrap_external", "builtins", "sys", "babylon60.shadow_tracer"):
                    # We also want to skip python internal frames where possible
                    filename = frame.f_code.co_filename
                    if "importlib" not in filename and "<frozen" not in filename:
                        return name
                frame = frame.f_back
        except Exception:
            pass
        return "unknown"

    def has_physical_module(self, fullname: str) -> bool:
        """Determines if a module has a physical file under the babylon60 directory."""
        if fullname in self.physical_cache:
            return self.physical_cache[fullname]

        # Convert module name to potential file paths relative to project root
        parts = fullname.split(".")
        # If looking at babylon60 itself
        if fullname == "babylon60":
            exists = (self.project_root / "babylon60" / "__init__.py").exists()
            self.physical_cache[fullname] = exists
            return exists

        # For submodules/packages
        subpath = Path(*parts)
        py_file = self.project_root / f"{subpath}.py"
        init_file = self.project_root / subpath / "__init__.py"
        
        exists = py_file.exists() or init_file.exists()
        self.physical_cache[fullname] = exists
        return exists

    def log_redirect(self, source, target, caller):
        self.redirects.append({
            "source": source,
            "target": target,
            "caller": caller
        })
        self.imports[caller].add(target)
        if self.ledger:
            self.ledger.log_resolution(caller, source, "REDIRECTED", target)

    def log_would_break(self, source, caller):
        # Only log if not already recorded for this caller/source combination
        if not any(x["source"] == source and x["caller"] == caller for x in self.would_breaks):
            self.would_breaks.append({
                "source": source,
                "caller": caller
            })
        self.imports[caller].add(source)
        if self.ledger:
            self.ledger.log_resolution(caller, source, "WOULD_BREAK", "None")

    def record_import(self, importer, imported):
        if importer and imported:
            if importer != "unknown" and importer != imported:
                # Filter to only care about cortex/babylon60 related imports
                if ("cortex" in importer or "babylon60" in importer) or ("cortex" in imported or "babylon60" in imported):
                    self.imports[importer].add(imported)
                    if self.ledger:
                        res_type = "DIRECT"
                        if "babylon60" in importer and "cortex" in imported:
                            res_type = "BYPASS"
                        self.ledger.log_resolution(importer, imported, res_type, "None")

    def install(self):
        """Installs the tracer hook into sys.meta_path and overrides standard import."""
        if self._installed:
            return
        
        # Initialize ledger if configured
        if os.environ.get("CORTEX_IMPORT_LEDGER") == "1" or os.environ.get("CORTEX_IMPORT_LEDGER") == "true":
            from babylon60.import_ledger import ImportResolutionLedger
            ledger_path = os.environ.get("CORTEX_IMPORT_LEDGER_PATH")
            self.ledger = ImportResolutionLedger(filepath=ledger_path)
            self.ledger.start_session()

        # Set up our shadow resolver at the top of meta_path
        self._resolver = ShadowResolver(self)
        sys.meta_path.insert(0, self._resolver)
        
        # Intercept builtin __import__ to build the dependency graph
        self._orig_import = __builtins__["__import__"]
        
        def custom_import(name, globals=None, locals=None, fromlist=(), level=0):
            caller = self.get_caller_module()
            module = self._orig_import(name, globals, locals, fromlist, level)
            
            # Record base module import
            self.record_import(caller, name)
            
            # Record elements from fromlist if specified
            if fromlist and hasattr(module, "__name__"):
                mod_name = module.__name__
                for item in fromlist:
                    sub_name = f"{mod_name}.{item}"
                    if sub_name in sys.modules:
                        self.record_import(caller, sub_name)
            return module
            
        __builtins__["__import__"] = custom_import
        self._installed = True

    def uninstall(self):
        """Restores original import and removes resolver hook."""
        if not self._installed:
            return
        if self._resolver in sys.meta_path:
            sys.meta_path.remove(self._resolver)
        __builtins__["__import__"] = self._orig_import
        self._installed = False
        if self.ledger:
            self.ledger.end_session()
            self.ledger = None

    def detect_cycles(self, collapsed: bool = False) -> list[list[str]]:
        """
        Detects cycles in the import graph using DFS.
        If collapsed is True, nodes are mapped from babylon60.* -> babylon60.* to simulate collapse stability.
        """
        # Build adjacency list
        graph = defaultdict(set)
        
        def map_node(node):
            if not collapsed:
                return node
            if node == "cortex":
                return "babylon60"
            if node.startswith("cortex."):
                return node.replace("cortex", "babylon60", 1)
            return node

        for u, neighbors in self.imports.items():
            mapped_u = map_node(u)
            for v in neighbors:
                mapped_v = map_node(v)
                if mapped_u != mapped_v:
                    graph[mapped_u].add(mapped_v)

        cycles = []
        visited = {}  # 0: unvisited, 1: visiting, 2: visited
        path = []

        def dfs(node):
            visited[node] = 1
            path.append(node)
            for neighbor in graph[node]:
                if visited.get(neighbor, 0) == 1:
                    # Cycle detected
                    idx = path.index(neighbor)
                    cycles.append(list(path[idx:]))
                elif visited.get(neighbor, 0) == 0:
                    dfs(neighbor)
            path.pop()
            visited[node] = 2

        for node in list(graph.keys()):
            if visited.get(node, 0) == 0:
                dfs(node)

        return cycles

    def export_compatibility_graph(self, filepath: str = "compatibility_delta_graph.json"):
        """Exports the collected compatibility metrics as a JSON DAG report."""
        uncollapsed_cycles = self.detect_cycles(collapsed=False)
        collapsed_cycles = self.detect_cycles(collapsed=True)
        
        # Serialize sets for JSON
        serializable_imports = {k: list(v) for k, v in self.imports.items()}
        
        report = {
            "mode": self.mode,
            "metrics": {
                "total_traced_modules": len(self.imports),
                "uncollapsed_cycles_count": len(uncollapsed_cycles),
                "collapsed_cycles_count": len(collapsed_cycles),
                "would_break_count": len(self.would_breaks),
                "redirects_count": len(self.redirects)
            },
            "uncollapsed_cycles": uncollapsed_cycles,
            "collapsed_cycles": collapsed_cycles,
            "would_breaks": self.would_breaks,
            "redirects": self.redirects,
            "import_graph": serializable_imports
        }
        
        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        
        return report

# Global tracer instance
_global_tracer = None

def enable_tracer(mode="present", force=False):
    global _global_tracer
    if _global_tracer is not None:
        if force:
            _global_tracer.uninstall()
            _global_tracer = None
        else:
            return _global_tracer
    _global_tracer = ImportTracer(mode=mode)
    _global_tracer.install()
    return _global_tracer

def disable_tracer(force=False):
    global _global_tracer
    if os.environ.get("CORTEX_SHADOW_MODE") and not force:
        # Do not disable the global session tracer during global run
        return
    if _global_tracer is not None:
        _global_tracer.uninstall()
        _global_tracer = None
