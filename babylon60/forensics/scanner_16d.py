from decimal import Decimal
# [C5-REAL] Exergy-Maximized
# scanner_16d.py — Extended Dimensional Scanner (Dims 14-16)
# Operator: borjamoskv | Kernel: MOSKV-1 APEX

import ast
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DimensionScore:
    """Puntuación de una dimensión individual."""
    dimension: int
    name: str
    score: Decimal           # 0.0 (catastrófico) - 1.0 (perfecto)
    metrics: dict[str, float] = field(default_factory=dict)
    findings: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# DIMENSIÓN 14: ENTROPÍA DE DEPENDENCIAS
# ═══════════════════════════════════════════════════════════

class DependencyEntropyScanner:
    """
    Mide la superficie de ataque y el bloat del árbol
    de dependencias.
    
    Principio: Cada dependencia transitiva que no usas
    directamente es anergía pura — coste sin retorno.
    """

    def __init__(self, project_root: Path):
        self.root = project_root

    def scan(self) -> DimensionScore:
        dep_tree = self._get_dependency_tree()
        direct_deps = self._get_direct_deps()
        imported = self._get_actually_imported()
        vulnerabilities = self._audit_vulnerabilities()

        total_transitive = len(dep_tree)
        max_depth = self._calculate_max_depth(dep_tree)
        actually_used = len(imported & set(dep_tree.keys()))
        bloat_ratio = (
            actually_used / total_transitive
            if total_transitive > 0 else 1.0
        )
        vuln_ratio = (
            vulnerabilities / total_transitive
            if total_transitive > 0 else 0.0
        )

        # Score compuesto
        depth_penalty = min(max_depth / 20.0, 1.0)
        score = max(0.0, 1.0 - (depth_penalty * (1 - bloat_ratio)))
        score *= (1.0 - vuln_ratio)

        findings = []
        if max_depth > 8:
            findings.append(
                f"ALERTA: Profundidad de deps = {max_depth} "
                f"(umbral: 8). Supply chain attack surface alta."
            )
        if bloat_ratio < 0.5:
            findings.append(
                f"ALERTA: Solo {actually_used}/{total_transitive} "
                f"deps son realmente importadas. Bloat = "
                f"{1 - bloat_ratio:.0%}"
            )
        if vulnerabilities > 0:
            findings.append(
                f"CRÍTICO: {vulnerabilities} deps con CVE conocidos."
            )

        return DimensionScore(
            dimension=14,
            name="Entropía de Dependencias",
            score=round(score, 3),
            metrics={
                "dep_depth": max_depth,
                "dep_count_transitive": total_transitive,
                "dep_count_direct": len(direct_deps),
                "dep_actually_used": actually_used,
                "dep_bloat_ratio": round(bloat_ratio, 3),
                "dep_vulnerabilities": vulnerabilities,
            },
            findings=findings
        )

    def _get_dependency_tree(self) -> dict[str, list[str]]:
        """Ejecuta pipdeptree para obtener el árbol completo."""
        try:
            result = subprocess.run(
                ["pipdeptree", "--json"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                tree_data = json.loads(result.stdout)
                return {
                    pkg["package"]["package_name"]: [
                        d["package_name"]
                        for d in pkg.get("dependencies", [])
                    ]
                    for pkg in tree_data
                }
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass
        return {}

    def _get_direct_deps(self) -> set[str]:
        """Lee requirements.txt o pyproject.toml."""
        req_file = self.root / "requirements.txt"
        if req_file.exists():
            deps = set()
            for line in req_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    name = line.split("==")[0].split(">=")[0].split("<")[0]
                    deps.add(name.strip().lower())
            return deps
        return set()

    def _get_actually_imported(self) -> set[str]:
        """Escanea todos los .py para encontrar imports reales."""
        imported = set()
        for py_file in self.root.rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported.add(
                                alias.name.split(".")[0].lower()
                            )
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imported.add(
                                node.module.split(".")[0].lower()
                            )
            except (SyntaxError, UnicodeDecodeError):
                continue
        return imported

    def _calculate_max_depth(
        self, tree: dict[str, list[str]]
    ) -> int:
        """DFS para encontrar la profundidad máxima del árbol."""
        visited: set[str] = set()

        def _dfs(pkg: str, depth: int) -> int:
            if pkg in visited or pkg not in tree:
                return depth
            visited.add(pkg)
            max_d = depth
            for dep in tree.get(pkg, []):
                max_d = max(max_d, _dfs(dep, depth + 1))
            visited.discard(pkg)
            return max_d

        return max(
            (_dfs(pkg, 0) for pkg in tree),
            default=0
        )

    def _audit_vulnerabilities(self) -> int:
        """Ejecuta pip-audit para contar CVEs."""
        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json", "--desc"],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode in (0, 1):
                data = json.loads(result.stdout)
                return len(data.get("vulnerabilities", []))
        except (subprocess.TimeoutExpired, FileNotFoundError,
                json.JSONDecodeError):
            pass
        return 0


# ═══════════════════════════════════════════════════════════
# DIMENSIÓN 15: FRICCIÓN DE ESTADO
# ═══════════════════════════════════════════════════════════

class StateFrictionScanner:
    """
    Detecta mutabilidad oculta y side-effects no declarados.
    
    Cada variable global mutable, cada default mutable,
    cada escritura a disco sin wrapper explícito es
    FRICCIÓN: energía desperdiciada en mantener coherencia
    mental sobre el estado real del sistema.
    """

    def __init__(self, project_root: Path):
        self.root = project_root

    def scan(self) -> DimensionScore:
        global_mutations = 0
        mutable_defaults = 0
        total_vars = 0
        hidden_state_vars = 0
        undeclared_io = 0
        files_scanned = 0

        for py_file in self.root.rglob("*.py"):
            try:
                source = py_file.read_text()
                tree = ast.parse(source)
                files_scanned += 1
            except (SyntaxError, UnicodeDecodeError):
                continue

            analysis = self._analyze_module(tree)
            global_mutations += analysis["global_mutations"]
            mutable_defaults += analysis["mutable_defaults"]
            total_vars += analysis["total_vars"]
            hidden_state_vars += analysis["hidden_state_vars"]
            undeclared_io += analysis["undeclared_io"]

        hidden_ratio = (
            hidden_state_vars / total_vars
            if total_vars > 0 else 0.0
        )
        score = max(0.0, 1.0 - hidden_ratio)

        findings = []
        if mutable_defaults > 0:
            findings.append(
                f"ANTIPATTERN: {mutable_defaults} funciones con "
                f"mutable defaults (def f(x=[])). Fuente de bugs "
                f"no deterministas."
            )
        if global_mutations > 10:
            findings.append(
                f"ALERTA: {global_mutations} mutaciones de estado "
                f"global detectadas. Cada una es un side-effect "
                f"que dificulta el razonamiento causal."
            )

        return DimensionScore(
            dimension=15,
            name="Fricción de Estado",
            score=round(score, 3),
            metrics={
                "global_mutations": global_mutations,
                "mutable_defaults": mutable_defaults,
                "undeclared_io": undeclared_io,
                "total_vars": total_vars,
                "hidden_state_vars": hidden_state_vars,
                "hidden_state_ratio": round(hidden_ratio, 4),
                "files_scanned": files_scanned,
            },
            findings=findings
        )

    def _analyze_module(self, tree: ast.Module) -> dict[str, int]:
        results = {
            "global_mutations": 0,
            "mutable_defaults": 0,
            "total_vars": 0,
            "hidden_state_vars": 0,
            "undeclared_io": 0,
        }

        for node in ast.walk(tree):
            # Detectar `global x` statements
            if isinstance(node, ast.Global):
                results["global_mutations"] += len(node.names)
                results["hidden_state_vars"] += len(node.names)

            # Detectar mutable defaults: def f(x=[]) o def f(x={})
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default and isinstance(
                        default, (ast.List, ast.Dict, ast.Set)
                    ):
                        results["mutable_defaults"] += 1

            # Contar asignaciones (aproximación de total_vars)
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                results["total_vars"] += 1

            # Detectar class variables (estado oculto a nivel de clase)
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.Assign, ast.AnnAssign)):
                        results["hidden_state_vars"] += 1
                        results["total_vars"] += 1

            # Detectar I/O no wrapeado (open(), print() a archivo)
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in (
                    "open", "print", "input"
                ):
                    results["undeclared_io"] += 1

        return results


# ═══════════════════════════════════════════════════════════
# DIMENSIÓN 16: ISOMORFISMO CAUSAL
# ═══════════════════════════════════════════════════════════

class CausalIsomorphismScanner:
    """
    Mide la densidad de código que produce efecto causal real
    vs código defensivo/teatro (Green Theater).
    
    Green Theater: Código que PARECE proteger pero que nunca
    se ejecuta bajo condiciones reales. Ej:
      - `if obj is None: return` cuando obj nunca es None
      - `try/except Exception:  # noqa: BLE001 pass` (silencia todo)
      - Dead branches (sin coverage)
    """

    def __init__(self, project_root: Path):
        self.root = project_root

    def scan(
        self, coverage_json_path: Path | None = None
    ) -> DimensionScore:
        total_loc = 0
        green_theater_loc = 0
        dead_branches = 0
        theater_patterns: list[str] = []

        for py_file in self.root.rglob("*.py"):
            try:
                source = py_file.read_text()
                lines = source.splitlines()
                tree = ast.parse(source)
                total_loc += len([
                    line for line in lines
                    if line.strip() and not line.strip().startswith("#")
                ])
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                # Pattern 1: Bare except with pass
                if isinstance(node, ast.ExceptHandler):
                    if (len(node.body) == 1
                            and isinstance(node.body[0], ast.Pass)):
                        green_theater_loc += 2
                        theater_patterns.append(
                            f"{py_file.name}:{node.lineno} "
                            f"except-pass (silenciador ciego)"
                        )

                # Pattern 2: if x is None: return (sin contexto)
                if isinstance(node, ast.If):
                    if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Is):
                        if len(node.test.comparators) == 1 and isinstance(node.test.comparators[0], ast.Constant) and node.test.comparators[0].value is None:
                            if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                                green_theater_loc += 2
                                theater_patterns.append(
                                    f"{py_file.name}:{node.lineno} "
                                    f"if-is-None-return (theatre pattern)"
                                )

        causal_density = (
            (total_loc - green_theater_loc) / total_loc
            if total_loc > 0 else 1.0
        )
        score = max(0.0, causal_density)
        
        findings = []
        if green_theater_loc > 0:
            findings.append(
                f"ALERTA: {green_theater_loc} lineas de Green Theater detectadas. "
                f"Patrones encontrados: {len(theater_patterns)}"
            )
            
        return DimensionScore(
            dimension=16,
            name="Isomorfismo Causal",
            score=round(score, 3),
            metrics={
                "total_loc": total_loc,
                "green_theater_loc": green_theater_loc,
                "dead_branches": dead_branches,
                "causal_density": round(causal_density, 3)
            },
            findings=findings
        )
