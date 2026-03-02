import ast
import itertools
from pathlib import Path


def get_ast_identifiers(filepath):
    with open(filepath, encoding="utf-8") as f:
        try:
            source = f.read()
            tree = ast.parse(source)
        except Exception:
            return set()

    identifiers = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            identifiers.add(node.id)
            continue
        if isinstance(node, ast.arg):
            identifiers.add(node.arg)
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            identifiers.add(node.name)
            continue
        if isinstance(node, ast.Attribute):
            identifiers.add(node.attr)
            continue
    return identifiers


def calculate_overlap(set_a, set_b):
    if not set_a or not set_b:
        return 0.0
    intersection = set_a.intersection(set_b)
    # Coeficiente de Solapamiento (Proxy Termodinámico para Información Mutua cruzada)
    return len(intersection) / min(len(set_a), len(set_b))


def main():
    base_dir = Path("/Users/borjafernandezangulo/cortex")
    target_dir = base_dir / "cortex"
    files = list(target_dir.rglob("*.py"))

    symbols_by_file = {}
    for f in files:
        if "venv" in f.parts or "test" in f.name or "migrations" in f.parts:
            continue
        symbols = get_ast_identifiers(f)
        if len(symbols) > 15:  # Filtrar vacuums termodinámicos
            symbols_by_file[f.relative_to(target_dir)] = symbols

    results = []
    file_list = list(symbols_by_file.keys())
    for f1, f2 in itertools.combinations(file_list, 2):
        overlap = calculate_overlap(symbols_by_file[f1], symbols_by_file[f2])
        results.append((overlap, f1, f2))

    results.sort(reverse=True, key=lambda x: x[0])

    print("=== HIGH MUTUAL INFORMATION (SHADOW DEPENDENCIES) ===")
    print("Score | Module A <-> Module B")
    print("-" * 65)
    high_coupling = [r for r in results if r[0] > 0.45]
    for score, f1, f2 in high_coupling[:15]:
        print(f"{score:.2f}  | {f1} <-> {f2}")

    if not high_coupling:
        print("No critical thermodynamic overlap found -> Arquitectura liminal preservada.")


if __name__ == "__main__":
    main()
