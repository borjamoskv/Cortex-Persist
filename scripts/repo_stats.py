import ast
import json
from pathlib import Path


def get_stats():
    base_dir = Path(__file__).parent.parent

    dirs_to_scan = [base_dir / "cortex", base_dir / "tests", base_dir / "sdks"]

    total_loc = 0
    total_modules = 0
    total_test_functions = 0
    total_test_classes = 0

    for d in dirs_to_scan:
        if not d.exists():
            continue

        for path in d.rglob("*.py"):
            total_modules += 1
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                    total_loc += len(content.splitlines())

                if "test_" in path.name or "test" in path.parts:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                            total_test_functions += 1
                        elif isinstance(node, ast.AsyncFunctionDef) and node.name.startswith(
                            "test_"
                        ):
                            total_test_functions += 1
                        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                            total_test_classes += 1
            except Exception as e:
                print(f"Error parsing {path}: {e}")

    return {
        "total_loc": total_loc,
        "total_modules": total_modules,
        "total_test_functions": total_test_functions,
        "total_test_classes": total_test_classes,
        "total_tests": total_test_functions,
    }


if __name__ == "__main__":
    stats = get_stats()

    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    out_file = artifacts_dir / "stats.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Stats written to {out_file}:")
    print(json.dumps(stats, indent=2))
