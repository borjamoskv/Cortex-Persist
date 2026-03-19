"""
DIKĒ-Ω Documentation Compliance Auditor.

Structural audit engine that cross-references code modules against documentation,
detects repetitive patterns via AST analysis, and scaffolds compliant boilerplate.

Capabilities:
  1. Exhaustive corpus census (closed corpus)
  2. Documentation compliance gap analysis
  3. System state synthesis
  4. Repetitive pattern detection (AST-level)
  5. Boilerplate scaffolding for new modules
"""

from __future__ import annotations

import ast
import collections
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = ["DocAuditor", "AuditReport", "PatternGroup", "CorpusCensus"]

logger = logging.getLogger(__name__)


@dataclass
class CorpusCensus:
    """Quantified snapshot of the repository."""

    total_py_files: int = 0
    total_loc: int = 0
    total_dirs: int = 0
    total_test_files: int = 0
    total_test_loc: int = 0
    total_extensions: int = 0
    ghost_files: int = 0
    psi_markers: int = 0
    sub_projects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_py_files": self.total_py_files,
            "total_loc": self.total_loc,
            "total_dirs": self.total_dirs,
            "total_test_files": self.total_test_files,
            "total_test_loc": self.total_test_loc,
            "total_extensions": self.total_extensions,
            "ghost_files": self.ghost_files,
            "psi_markers": self.psi_markers,
            "sub_projects": self.sub_projects,
        }


@dataclass
class PatternGroup:
    """A group of duplicate function bodies detected via AST hashing."""

    hash: str
    locations: list[tuple[str, str, int, int]]  # (path, func_name, line, stmt_count)

    @property
    def count(self) -> int:
        return len(self.locations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hash": self.hash[:8],
            "count": self.count,
            "representative": self.locations[0][1],
            "stmt_count": self.locations[0][3],
            "locations": [
                {"path": loc[0], "name": loc[1], "line": loc[2]}
                for loc in self.locations
            ],
        }


@dataclass
class DocGap:
    """A documentation gap: module without docs or docs without module."""

    module_path: str
    gap_type: str  # "undocumented_module", "orphan_doc", "missing_docstring"
    severity: str  # "high", "medium", "low"
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_path": self.module_path,
            "gap_type": self.gap_type,
            "severity": self.severity,
            "suggestion": self.suggestion,
        }


@dataclass
class AuditReport:
    """Full audit report produced by DIKĒ-Ω."""

    census: CorpusCensus
    doc_gaps: list[DocGap] = field(default_factory=list)
    pattern_groups: list[PatternGroup] = field(default_factory=list)
    psi_locations: list[dict[str, Any]] = field(default_factory=list)
    top_files_by_loc: list[tuple[str, int]] = field(default_factory=list)
    compliance_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "census": self.census.to_dict(),
            "doc_gaps": [g.to_dict() for g in self.doc_gaps],
            "duplicate_patterns": [p.to_dict() for p in self.pattern_groups],
            "psi_markers": self.psi_locations[:20],
            "top_files_by_loc": [
                {"path": p, "loc": loc} for p, loc in self.top_files_by_loc[:20]
            ],
            "compliance_score": round(self.compliance_score, 2),
        }


_PSI_MARKERS = ("TODO", "FIXME", "HACK", "XXX")


class DocAuditor:
    """DIKĒ-Ω audit engine.

    Performs structural cross-referencing between code and documentation,
    detects repetitive AST patterns, and quantifies the corpus.
    """

    def __init__(self, repo_root: str | Path) -> None:
        self.root = Path(repo_root)
        self.cortex_dir = self.root / "cortex"
        self.tests_dir = self.root / "tests"
        self.docs_dir = self.root / "docs"

    # ── 1. Corpus Census ─────────────────────────────────────────────

    def census(self) -> CorpusCensus:
        """Produce a quantified census of the repository."""
        c = CorpusCensus()
        c.total_py_files, c.total_loc = self._count_py(self.cortex_dir)
        c.total_test_files, c.total_test_loc = self._count_py(self.tests_dir)
        c.total_dirs = sum(
            1
            for _ in self.cortex_dir.rglob("*")
            if _.is_dir() and "__pycache__" not in str(_)
        )
        c.total_extensions = sum(
            1
            for d in (self.cortex_dir / "extensions").iterdir()
            if d.is_dir() and d.name != "__pycache__"
        ) if (self.cortex_dir / "extensions").exists() else 0

        c.ghost_files = sum(
            1 for f in self.root.iterdir() if f.name.startswith("file:mem_")
        )
        c.psi_markers = self._count_psi_markers()
        c.sub_projects = [
            d.name
            for d in sorted(self.root.iterdir())
            if d.is_dir()
            and not d.name.startswith(".")
            and d.name
            not in {
                "cortex",
                "tests",
                "docs",
                "cortex_persist.egg-info",
                "__pycache__",
            }
        ]
        return c

    # ── 2. Documentation Compliance ──────────────────────────────────

    def audit_doc_compliance(self) -> list[DocGap]:
        """Cross-reference cortex/ modules against docs/."""
        gaps: list[DocGap] = []
        doc_files = {
            p.stem.lower()
            for p in self.docs_dir.rglob("*.md")
        } if self.docs_dir.exists() else set()

        # Check each top-level cortex submodule for documentation
        if self.cortex_dir.exists():
            for child in sorted(self.cortex_dir.iterdir()):
                if not child.is_dir() or child.name.startswith("_"):
                    continue
                module_name = child.name.lower()
                if module_name not in doc_files:
                    gaps.append(DocGap(
                        module_path=f"cortex/{child.name}/",
                        gap_type="undocumented_module",
                        severity="high" if child.name in {
                            "engine", "memory", "ledger", "guards",
                            "storage", "crypto", "database",
                        } else "medium",
                        suggestion=f"Create docs/{child.name}.md",
                    ))

        # Check for public functions without docstrings in critical modules
        critical_modules = ["engine", "memory", "guards", "ledger", "storage"]
        for mod_name in critical_modules:
            mod_path = self.cortex_dir / mod_name
            if not mod_path.exists():
                continue
            for py_file in mod_path.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue
                try:
                    tree = ast.parse(py_file.read_text(encoding="utf-8"))
                except (SyntaxError, UnicodeDecodeError):
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name.startswith("_"):
                            continue
                        if not ast.get_docstring(node):
                            gaps.append(DocGap(
                                module_path=str(py_file.relative_to(self.root)),
                                gap_type="missing_docstring",
                                severity="medium",
                                suggestion=f"Add docstring to {node.name}() "
                                           f"at line {node.lineno}",
                            ))
        return gaps

    # ── 3. Repetitive Pattern Detection ──────────────────────────────

    def detect_patterns(self, min_stmts: int = 3) -> list[PatternGroup]:
        """AST-level duplicate function body detection."""
        func_hashes: dict[str, list[tuple[str, str, int, int]]] = (
            collections.defaultdict(list)
        )
        for py_file in self.cortex_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            rel = str(py_file.relative_to(self.root))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if len(node.body) < min_stmts:
                        continue
                    body_str = ast.dump(
                        ast.Module(body=node.body, type_ignores=[])
                    )
                    h = hashlib.md5(body_str.encode()).hexdigest()
                    func_hashes[h].append(
                        (rel, node.name, node.lineno, len(node.body))
                    )

        return [
            PatternGroup(hash=h, locations=locs)
            for h, locs in func_hashes.items()
            if len(locs) > 1
        ]

    # ── 4. Full Audit ────────────────────────────────────────────────

    def run(self) -> AuditReport:
        """Execute full DIKĒ-Ω audit and return structured report."""
        census_data = self.census()
        doc_gaps = self.audit_doc_compliance()
        patterns = self.detect_patterns()
        psi = self._find_psi_markers()
        top_files = self._top_files_by_loc(20)

        total_checks = max(len(doc_gaps) + 5, 1)  # baseline checks
        passed = total_checks - len([g for g in doc_gaps if g.severity == "high"])
        score = (passed / total_checks) * 100

        return AuditReport(
            census=census_data,
            doc_gaps=doc_gaps,
            pattern_groups=patterns,
            psi_locations=psi,
            top_files_by_loc=top_files,
            compliance_score=score,
        )

    # ── 5. Boilerplate Scaffolding ───────────────────────────────────

    @staticmethod
    def scaffold_module(
        name: str,
        parent: str = "cortex/extensions",
    ) -> dict[str, str]:
        """Generate compliant scaffolding for a new CORTEX module.

        Returns a dict mapping relative file paths to their content.
        """
        mod_path = f"{parent}/{name}"
        files: dict[str, str] = {}

        files[f"{mod_path}/__init__.py"] = (
            f'"""\n{name.replace("_", " ").title()} extension for CORTEX.\n"""\n\n'
            f"__all__: list[str] = []\n"
        )

        files[f"{mod_path}/core.py"] = (
            f'"""\nCore logic for {name}.\n"""\n\n'
            f"from __future__ import annotations\n\n"
            f"import logging\n\n"
            f'logger = logging.getLogger(__name__)\n\n\n'
            f"class {name.title().replace('_', '')}Manager:\n"
            f'    """Manager for {name} operations."""\n\n'
            f"    def __init__(self) -> None:\n"
            f'        """Initialize {name} manager."""\n'
            f"        self._initialized = False\n\n"
            f"    async def run(self) -> dict:\n"
            f'        """Execute {name} operation."""\n'
            f"        raise NotImplementedError\n"
        )

        files[f"tests/test_{name}.py"] = (
            f'"""Tests for {name} module."""\n\n'
            f"import pytest\n\n"
            f"from {parent.replace('/', '.')}.{name}.core "
            f"import {name.title().replace('_', '')}Manager\n\n\n"
            f"class Test{name.title().replace('_', '')}Manager:\n"
            f'    """Test suite for {name}."""\n\n'
            f"    def test_init(self) -> None:\n"
            f"        mgr = {name.title().replace('_', '')}Manager()\n"
            f"        assert not mgr._initialized\n\n"
            f"    @pytest.mark.asyncio\n"
            f"    async def test_run_not_implemented(self) -> None:\n"
            f"        mgr = {name.title().replace('_', '')}Manager()\n"
            f"        with pytest.raises(NotImplementedError):\n"
            f"            await mgr.run()\n"
        )

        files[f"docs/{name}.md"] = (
            f"# {name.replace('_', ' ').title()}\n\n"
            f"## Overview\n\n"
            f"TODO: Document the {name} module.\n\n"
            f"## API Reference\n\n"
            f"See `{mod_path}/core.py` for the public API.\n"
        )

        return files

    # ── Private helpers ──────────────────────────────────────────────

    def _count_py(self, directory: Path) -> tuple[int, int]:
        """Count Python files and total LOC in a directory."""
        files = loc = 0
        if not directory.exists():
            return 0, 0
        for p in directory.rglob("*.py"):
            if "__pycache__" in str(p):
                continue
            files += 1
            try:
                loc += sum(1 for _ in p.open(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                pass
        return files, loc

    def _count_psi_markers(self) -> int:
        """Count TODO/FIXME/HACK/XXX markers in cortex/."""
        count = 0
        for p in self.cortex_dir.rglob("*.py"):
            if "__pycache__" in str(p):
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for marker in _PSI_MARKERS:
                count += text.count(marker)
        return count

    def _find_psi_markers(self) -> list[dict[str, Any]]:
        """Find PSI marker locations."""
        results: list[dict[str, Any]] = []
        for p in self.cortex_dir.rglob("*.py"):
            if "__pycache__" in str(p):
                continue
            try:
                lines = p.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            rel = str(p.relative_to(self.root))
            for i, line in enumerate(lines, 1):
                for marker in _PSI_MARKERS:
                    if marker in line:
                        results.append({
                            "file": rel,
                            "line": i,
                            "marker": marker,
                            "content": line.strip()[:120],
                        })
        return results

    def _top_files_by_loc(self, n: int = 20) -> list[tuple[str, int]]:
        """Get top N files by line count."""
        file_locs: list[tuple[str, int]] = []
        for p in self.cortex_dir.rglob("*.py"):
            if "__pycache__" in str(p):
                continue
            try:
                loc = sum(1 for _ in p.open(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                continue
            file_locs.append((str(p.relative_to(self.root)), loc))
        file_locs.sort(key=lambda x: -x[1])
        return file_locs[:n]
