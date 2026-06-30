"""
CORTEX Ecosystem Master Exergy Inventory — Dynamic Compiler v2.0

Discovers all skills, workflows, scripts, and plugin skills from the
filesystem, computes exergy scores via AST analysis (Python) or
code-block ratio (Markdown/Shell), and outputs a ranked markdown
inventory with clickable file:// links.

Zero external dependencies — stdlib only.
Author: Borja Moskv (SYS_ID borjamoskv)
Reality Level: C5-REAL
"""
from __future__ import annotations

import ast
import statistics
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants — Dynamic home resolution to prevent PII Bleed
# ---------------------------------------------------------------------------
HOME = Path.home()
WORKSPACE_ROOT = HOME / "30_CORTEX"
GLOBAL_SKILLS_ROOT = HOME / ".gemini" / "config" / "skills"
PLUGINS_ROOT = HOME / ".gemini" / "config" / "plugins"
ACTIVE_WORKFLOWS_DIR = WORKSPACE_ROOT / ".agents" / "workflows"
COLD_STORAGE_WORKFLOWS = HOME / "COLD_STORAGE" / "cortex-config" / "workflows"
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"
INVENTORY_MD_PATH = WORKSPACE_ROOT / "docs" / "CORTEX_EXERGY_INVENTORY.md"

# Internal scripts to skip (tooling, not ecosystem components)
SKIP_SCRIPTS = {
    "_audit.py",
    "_changed_files.py",
    "__init__.py",
    "compile_exergy_inventory.py",
}

# Directories to exclude from any recursive walk
EXCLUDE_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    "experimental",
    ".venv",
    "venv",
    "dist",
    "build",
    ".tox",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Component:
    """A single ecosystem component with computed exergy."""

    name: str
    component_type: str  # Skill | Workflow | Script | Plugin Skill
    abs_path: Path
    status: str  # Active | Tombstoned | Archived | Cold Storage
    exergy: float = 0.0
    confidence: str = "C4"
    scoring_method: str = "heuristic"
    line_count: int = 0
    extra: dict = field(default_factory=dict)

    @property
    def safe_link(self) -> str:
        """Return a PII-safe file:// markdown link."""
        safe = str(self.abs_path).replace(str(HOME), "~")
        return f"[{self.name}](file://{safe})"


# ---------------------------------------------------------------------------
# Phase 1: Discovery
# ---------------------------------------------------------------------------
def discover_skills(root: Path, status: str) -> list[Component]:
    """Discover SKILL.md files under a directory (one level deep)."""
    results: list[Component] = []
    if not root.is_dir():
        return results
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name.startswith("_"):
            continue
        skill_md = child / "SKILL.md"
        if skill_md.is_file():
            results.append(
                Component(
                    name=child.name,
                    component_type="Skill",
                    abs_path=skill_md,
                    status=status,
                )
            )
    return results


def discover_tombstoned_skills() -> list[Component]:
    tomb_dir = GLOBAL_SKILLS_ROOT / ".tombstone"
    results: list[Component] = []
    if not tomb_dir.is_dir():
        return results
    for child in sorted(tomb_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if skill_md.is_file():
            results.append(
                Component(
                    name=child.name,
                    component_type="Skill",
                    abs_path=skill_md,
                    status="Tombstoned",
                )
            )
    return results


def discover_archived_skills() -> list[Component]:
    arch_dir = GLOBAL_SKILLS_ROOT / "_archived"
    results: list[Component] = []
    if not arch_dir.is_dir():
        return results
    for child in sorted(arch_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if skill_md.is_file():
            results.append(
                Component(
                    name=child.name,
                    component_type="Skill",
                    abs_path=skill_md,
                    status="Archived",
                )
            )
    return results


def discover_plugin_skills() -> list[Component]:
    """Walk plugins/*/skills/*/SKILL.md."""
    results: list[Component] = []
    if not PLUGINS_ROOT.is_dir():
        return results
    for plugin_dir in sorted(PLUGINS_ROOT.iterdir()):
        if not plugin_dir.is_dir():
            continue
        skills_dir = plugin_dir / "skills"
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if skill_md.is_file():
                results.append(
                    Component(
                        name=f"{plugin_dir.name}/{skill_dir.name}",
                        component_type="Plugin Skill",
                        abs_path=skill_md,
                        status="Active (Plugin)",
                    )
                )
    return results


def discover_workflows(directory: Path, status: str) -> list[Component]:
    """Discover .md workflow files in a directory (non-recursive)."""
    results: list[Component] = []
    if not directory.is_dir():
        return results
    for f in sorted(directory.iterdir()):
        if f.is_file() and f.suffix == ".md":
            # Skip archive subdirectories
            if f.name.startswith("_"):
                continue
            results.append(
                Component(
                    name=f.stem,
                    component_type="Workflow",
                    abs_path=f,
                    status=status,
                )
            )
    return results


def discover_scripts() -> list[Component]:
    """Discover .py and .sh scripts in SCRIPTS_DIR."""
    results: list[Component] = []
    if not SCRIPTS_DIR.is_dir():
        return results
    for f in sorted(SCRIPTS_DIR.iterdir()):
        if not f.is_file():
            continue
        if f.name in SKIP_SCRIPTS:
            continue
        if f.suffix in (".py", ".sh"):
            results.append(
                Component(
                    name=f.name,
                    component_type="Script",
                    abs_path=f,
                    status="Active",
                )
            )
    return results


def discover_all() -> list[Component]:
    """Run full discovery across all 7 sources."""
    components: list[Component] = []

    # Skills
    components.extend(discover_skills(GLOBAL_SKILLS_ROOT, "Active"))
    components.extend(discover_tombstoned_skills())
    components.extend(discover_archived_skills())
    components.extend(discover_plugin_skills())

    # Workflows
    components.extend(discover_workflows(ACTIVE_WORKFLOWS_DIR, "Active"))
    components.extend(discover_workflows(COLD_STORAGE_WORKFLOWS, "Cold Storage"))

    # Scripts
    components.extend(discover_scripts())

    return components


# ---------------------------------------------------------------------------
# Phase 2: Scoring
# ---------------------------------------------------------------------------
class ComplexityVisitor(ast.NodeVisitor):
    """Compute McCabe-style cyclomatic complexity and max nesting depth."""

    def __init__(self) -> None:
        self.complexity: int = 1  # base complexity
        self.max_depth: int = 0
        self._current_depth: int = 0
        self.function_count: int = 0
        self.class_count: int = 0
        self.import_count: int = 0

    def _enter_branch(self, node: ast.AST) -> None:
        self.complexity += 1
        self._current_depth += 1
        self.max_depth = max(self.max_depth, self._current_depth)
        self.generic_visit(node)
        self._current_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self._enter_branch(node)

    def visit_For(self, node: ast.For) -> None:
        self._enter_branch(node)

    def visit_While(self, node: ast.While) -> None:
        self._enter_branch(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._enter_branch(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._enter_branch(node)

    def visit_With(self, node: ast.With) -> None:
        self._enter_branch(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each additional boolean connector adds complexity
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_count += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_count += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_count += 1
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        self.import_count += len(node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.import_count += len(node.names) if node.names else 1


def score_python(path: Path) -> tuple[float, str, dict]:
    """Score a Python file using AST analysis. Returns (score, method, extra)."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 50.0, "error", {}

    lines = source.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return 0.0, "empty", {}

    # Non-blank, non-comment lines
    code_lines = sum(
        1 for ln in lines if ln.strip() and not ln.strip().startswith("#")
    )

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        # Fallback: ratio-based scoring
        ratio = code_lines / total_lines if total_lines > 0 else 0.0
        return round(50.0 + ratio * 40.0, 1), "syntax-fallback", {
            "total_lines": total_lines,
        }

    visitor = ComplexityVisitor()
    visitor.visit(tree)

    # Entropy components (all normalized 0..1, lower is better)
    # McCabe: complexity per code line (bounded)
    mccabe_density = min(visitor.complexity / max(code_lines, 1), 1.0)
    # Nesting: max depth normalized (8+ is extreme)
    nesting_norm = min(visitor.max_depth / 8.0, 1.0)
    # Import density: imports per code line (high = glue code)
    import_density = min(visitor.import_count / max(code_lines, 1), 1.0)
    # Size penalty: very small files (< 10 lines) get penalized
    size_factor = min(code_lines / 10.0, 1.0)

    # Weighted entropy (0..1)
    entropy = (
        0.35 * mccabe_density
        + 0.25 * nesting_norm
        + 0.20 * import_density
        + 0.20 * (1.0 - size_factor)
    )

    score = max(0.0, min(100.0, 100.0 - (entropy * 100.0)))

    extra = {
        "total_lines": total_lines,
        "code_lines": code_lines,
        "complexity": visitor.complexity,
        "max_depth": visitor.max_depth,
        "functions": visitor.function_count,
        "classes": visitor.class_count,
        "imports": visitor.import_count,
    }

    return round(score, 1), "AST", extra


def score_markdown(path: Path) -> tuple[float, str, dict]:
    """Score a Markdown file by ratio of fenced code blocks to total lines."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return 50.0, "error", {}

    total = len(lines)
    if total == 0:
        return 50.0, "empty", {}

    in_code = False
    code_lines = 0
    yaml_blocks = 0

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            if in_code and ("yaml" in stripped or "python" in stripped):
                yaml_blocks += 1
            continue
        if in_code:
            code_lines += 1

    ratio = code_lines / total
    # Bonus for structured content (YAML blocks indicate executable specs)
    structure_bonus = min(yaml_blocks * 2.0, 10.0)

    score = 50.0 + (ratio * 45.0) + structure_bonus
    score = max(0.0, min(100.0, score))

    return round(score, 1), "code-block-ratio", {
        "total_lines": total,
        "code_lines": code_lines,
        "yaml_blocks": yaml_blocks,
    }


def score_shell(path: Path) -> tuple[float, str, dict]:
    """Score a shell script by command density."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return 50.0, "error", {}

    total = len(lines)
    if total == 0:
        return 50.0, "empty", {}

    exec_lines = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        exec_lines += 1

    ratio = exec_lines / total
    size_factor = min(exec_lines / 10.0, 1.0)
    score = 50.0 + (ratio * 40.0) + (size_factor * 10.0)
    score = max(0.0, min(100.0, score))

    return round(score, 1), "command-density", {
        "total_lines": total,
        "exec_lines": exec_lines,
    }


def score_component(comp: Component) -> None:
    """Compute exergy score for a component based on file type."""
    suffix = comp.abs_path.suffix.lower()

    if suffix == ".py":
        comp.exergy, comp.scoring_method, comp.extra = score_python(comp.abs_path)
        comp.confidence = "C5"
    elif suffix == ".md":
        comp.exergy, comp.scoring_method, comp.extra = score_markdown(comp.abs_path)
        comp.confidence = "C4"
    elif suffix == ".sh":
        comp.exergy, comp.scoring_method, comp.extra = score_shell(comp.abs_path)
        comp.confidence = "C4"
    else:
        comp.exergy = 50.0
        comp.scoring_method = "default"
        comp.confidence = "C3"

    comp.line_count = comp.extra.get("total_lines", 0)


# ---------------------------------------------------------------------------
# Phase 3: Output
# ---------------------------------------------------------------------------
def render_inventory(components: list[Component]) -> str:
    """Render the full markdown inventory document."""
    # Sort: exergy DESC, then name ASC for stability
    components.sort(key=lambda c: (-c.exergy, c.name.lower()))

    # Statistics
    scores = [c.exergy for c in components]
    total = len(scores)
    mean_score = statistics.mean(scores) if scores else 0.0
    median_score = statistics.median(scores) if scores else 0.0
    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 0.0

    # Type counts
    type_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for c in components:
        type_counts[c.component_type] = type_counts.get(c.component_type, 0) + 1
        status_counts[c.status] = status_counts.get(c.status, 0) + 1

    lines: list[str] = []

    # Header
    lines.append("# CORTEX Ecosystem Master Exergy Inventory")
    lines.append("")
    lines.append(
        "Consolidated thermodynamic exergy ranking of all SKILLS, SCRIPTS,"
        " WORKFLOWS, and PLUGIN SKILLS in the CORTEX ecosystem."
    )
    lines.append("")
    lines.append("* **Reality Level**: C5-REAL (Dynamic AST + code-block telemetry)")
    lines.append(f"* **Date**: {date.today().isoformat()}")
    lines.append("* **Compiler**: `scripts/compile_exergy_inventory.py` v2.0")
    lines.append("")

    # Summary statistics
    lines.append("## Summary")
    lines.append("")
    lines.append("```yaml")
    lines.append(f"total_components: {total}")
    lines.append(f"exergy_mean: {mean_score:.1f}")
    lines.append(f"exergy_median: {median_score:.1f}")
    lines.append(f"exergy_min: {min_score:.1f}")
    lines.append(f"exergy_max: {max_score:.1f}")
    lines.append("type_distribution:")
    for t, count in sorted(type_counts.items()):
        lines.append(f"  {t}: {count}")
    lines.append("status_distribution:")
    for s, count in sorted(status_counts.items()):
        lines.append(f"  {s}: {count}")
    lines.append("```")
    lines.append("")

    # Justification Logic
    lines.append("---")
    lines.append("")
    lines.append("## Justification Logic")
    lines.append("")
    lines.append("```yaml")
    lines.append("Python_scoring:")
    lines.append("  method: AST analysis via ast.parse()")
    lines.append("  formula: 100.0 - (weighted_entropy * 100.0)")
    lines.append("  weights:")
    lines.append("    mccabe_density: 0.35")
    lines.append("    nesting_depth: 0.25")
    lines.append("    import_density: 0.20")
    lines.append("    size_penalty: 0.20")
    lines.append("  confidence: C5")
    lines.append("")
    lines.append("Markdown_scoring:")
    lines.append("  method: Code block ratio + YAML structure bonus")
    lines.append("  formula: 50.0 + (code_ratio * 45.0) + min(yaml_blocks * 2, 10)")
    lines.append("  confidence: C4")
    lines.append("")
    lines.append("Shell_scoring:")
    lines.append("  method: Command density analysis")
    lines.append("  formula: 50.0 + (exec_ratio * 40.0) + (size_factor * 10.0)")
    lines.append("  confidence: C4")
    lines.append("```")
    lines.append("")

    # Master table by section
    sections = [
        ("Active Skills", lambda c: c.component_type == "Skill" and c.status == "Active"),
        ("Tombstoned Skills", lambda c: c.component_type == "Skill" and c.status == "Tombstoned"),
        ("Archived Skills", lambda c: c.component_type == "Skill" and c.status == "Archived"),
        ("Plugin Skills", lambda c: c.component_type == "Plugin Skill"),
        ("Active Workflows", lambda c: c.component_type == "Workflow" and c.status == "Active"),
        ("Cold Storage Workflows", lambda c: c.component_type == "Workflow" and c.status == "Cold Storage"),
        ("Scripts", lambda c: c.component_type == "Script"),
    ]

    rank = 1
    lines.append("---")
    lines.append("")

    for section_name, predicate in sections:
        section_items = [c for c in components if predicate(c)]
        if not section_items:
            continue

        lines.append(f"## {section_name}")
        lines.append("")
        lines.append("| # | Component | Exergy | Scoring | Lines | Confidence |")
        lines.append("|---|-----------|--------|---------|-------|------------|")

        for comp in section_items:
            lines.append(
                f"| {rank} "
                f"| {comp.safe_link} "
                f"| **{comp.exergy}** "
                f"| {comp.scoring_method} "
                f"| {comp.line_count} "
                f"| {comp.confidence} |"
            )
            rank += 1

        lines.append("")

    # Verification Matrices
    lines.append("---")
    lines.append("")
    lines.append("## Verification Matrices")
    lines.append("")

    lines.append("### Primitives (`prims`)")
    prims = [
        "**Exergy Gradient**: Rate of useful work output relative to total resource consumption.",
        "**Thermodynamic Lane**: Designated execution path with strict resource and scheduling constraints.",
        "**AST Isomorphism**: Structural equivalence of syntax trees, invariant under naming mutations.",
        "**C5-REAL Validation**: Cryptographically verified, deterministic execution output.",
        "**Consensus Quorum**: Byzantine fault tolerant agreement across modular agent networks.",
        "**McCabe Density**: Cyclomatic complexity normalized per line of executable code.",
        "**Code-Block Ratio**: Proportion of fenced code blocks in markdown documents.",
        "**Import Density**: Number of imported symbols per executable line (glue-code indicator).",
        "**Nesting Depth**: Maximum control-flow nesting level in a function body.",
        "**Size Factor**: Executable line count normalized against minimum viable threshold.",
    ]
    for i, p in enumerate(prims, 1):
        lines.append(f"{i}. {p}")
    lines.append("")

    lines.append("### Invariants (`invt`)")
    invts = [
        "**Absolute Attributability**: Every fact requires a cryptographically signed attribution token.",
        "**No Silent Death**: Background workers must catch and propagate exceptions with trace.",
        "**Single State Authority**: Persistent mutations go exclusively through the Saga write contract.",
        "**Deterministic Scoring**: Same filesystem state always produces identical exergy rankings.",
        "**PII Containment**: No absolute home directory paths appear in committed output.",
        "**Discovery Completeness**: Every SKILL.md, workflow .md, and script on disk appears in inventory.",
        "**Monotonic Ranking**: Output is strictly sorted by exergy DESC, name ASC.",
    ]
    for i, inv in enumerate(invts, 1):
        lines.append(f"{i}. {inv}")
    lines.append("")

    lines.append("### Anti-Patterns (`antip`)")
    antips = [
        "**Limerence Loop**: Token expenditure on redundant iterations without state mutation.",
        "**Context Leakage**: Merging metadata or credentials across tenant-isolated boundaries.",
        "**Prose Padding**: Decorative conversational wrappers enclosing factual outputs.",
        "**Ghost Components**: Inventory entries referencing paths that do not exist on disk.",
        "**Static Freezing**: Hardcoded scores that never update with code changes.",
        "**Walk Explosion**: Recursive directory traversal into node_modules or .git.",
    ]
    for i, ap in enumerate(antips, 1):
        lines.append(f"{i}. {ap}")
    lines.append("")

    lines.append("### Redundancies (`redun`)")
    reduns = [
        "**Fallback Consensus**: Multi-model routing when primary cognitive engines drift.",
        "**Ledger Replication**: Redundant ledger records across local and network trust engines.",
        "**Tombstone Retention**: Preserving scored entries for deprecated skills for historical audit.",
    ]
    for i, r in enumerate(reduns, 1):
        lines.append(f"{i}. {r}")
    lines.append("")

    lines.append("### Adversarial Vectors (`reda`)")
    redas = [
        "**Isomorphic Bypass**: Structurally identical malicious payloads via semantic transformations.",
        "**Deadlock Induction**: Concurrent read-write locks designed to freeze SQLite event loops.",
        "**Score Inflation**: Artificially reducing McCabe complexity by splitting into trivial functions.",
        "**PII Exfiltration**: Embedding absolute paths in markdown links to leak host identity.",
    ]
    for i, rd in enumerate(redas, 1):
        lines.append(f"{i}. {rd}")
    lines.append("")

    lines.append("`SYS_ID borjamoskv`")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    # Phase 1: Discover
    components = discover_all()
    print(f"[Phase 1] Discovered {len(components)} components")

    # Phase 2: Score
    for comp in components:
        score_component(comp)
    print(f"[Phase 2] Scored {len(components)} components")

    # Phase 3: Output
    content = render_inventory(components)
    INVENTORY_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_MD_PATH.write_text(content, encoding="utf-8")
    print(f"[Phase 3] Written to {INVENTORY_MD_PATH}")

    # Summary
    scores = [c.exergy for c in components]
    print(f"\nC5-REAL: {len(components)} components | "
          f"Mean: {statistics.mean(scores):.1f} | "
          f"Median: {statistics.median(scores):.1f} | "
          f"Range: [{min(scores):.1f}, {max(scores):.1f}]")


if __name__ == "__main__":
    main()
