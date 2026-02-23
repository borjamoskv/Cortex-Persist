#!/usr/bin/env python3
"""Squad β — Mass __all__ Injection.

Scans all Python modules in cortex/ for missing __all__ declarations
and adds them by detecting public functions/classes.

LEGIØN-1 Swarm Agent: Automated encapsulation hardening.
"""

import ast
import sys
from pathlib import Path


def get_public_names(filepath: Path) -> list[str]:
    """Extract public function/class names from a Python file."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    names: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                names.append(node.name)
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                names.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    # Only include UPPER_CASE constants
                    if target.id.isupper() or target.id == target.id.upper():
                        names.append(target.id)
    return names


def has_all_declaration(filepath: Path) -> bool:
    """Check if __all__ already exists."""
    source = filepath.read_text(encoding="utf-8")
    return "__all__" in source


def find_insertion_point(source: str) -> int:
    """Find the line index after module docstring and imports."""
    lines = source.split("\n")
    tree = ast.parse(source)

    # Find last import statement line
    last_import_line = 0
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last_import_line = max(last_import_line, node.end_lineno or node.lineno)

    # If no imports, insert after docstring
    if last_import_line == 0:
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                return node.end_lineno
        return 0

    return last_import_line


def inject_all(filepath: Path, names: list[str], dry_run: bool = False) -> bool:
    """Inject __all__ into a file."""
    if not names:
        return False

    source = filepath.read_text(encoding="utf-8")
    lines = source.split("\n")
    insert_after = find_insertion_point(source)

    # Format __all__
    if len(names) <= 3:
        all_str = f"__all__ = {names!r}"
    else:
        items = ",\n    ".join(f'"{n}"' for n in sorted(names))
        all_str = f"__all__ = [\n    {items},\n]"

    if dry_run:
        print(f"  Would inject into {filepath}: {names}")
        return True

    # Insert after the insertion point
    lines.insert(insert_after, "")
    lines.insert(insert_after + 1, all_str)

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return True


def main():
    dry_run = "--dry-run" in sys.argv
    cortex_dir = Path(__file__).parent.parent / "cortex"

    if not cortex_dir.exists():
        print(f"Error: {cortex_dir} not found")
        sys.exit(1)

    total = 0
    injected = 0
    skipped = 0

    for py_file in sorted(cortex_dir.rglob("*.py")):
        # Skip __init__.py, __main__.py, __pycache__
        if py_file.name in ("__init__.py", "__main__.py"):
            continue
        if "__pycache__" in str(py_file):
            continue

        total += 1

        if has_all_declaration(py_file):
            skipped += 1
            continue

        names = get_public_names(py_file)
        if not names:
            if not dry_run:
                print(f"  ⚠ No public names in {py_file.relative_to(cortex_dir)}")
            skipped += 1
            continue

        rel = py_file.relative_to(cortex_dir)
        if inject_all(py_file, names, dry_run=dry_run):
            injected += 1
            action = "Would inject" if dry_run else "✅ Injected"
            print(f"  {action} __all__ into {rel} ({len(names)} exports)")

    print(f"\n{'DRY RUN ' if dry_run else ''}Summary:")
    print(f"  Total modules scanned: {total}")
    print(f"  Injected __all__:      {injected}")
    print(f"  Already had / skipped: {skipped}")


if __name__ == "__main__":
    main()
