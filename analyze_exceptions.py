import ast
import os


def count_exceptions_in_file(path: str) -> tuple[int, int, int]:
    bare, bound, total = 0, 0, 0
    with open(path) as file:
        try:
            tree = ast.parse(file.read(), filename=path)
        except Exception:
            return bare, bound, total

        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            total += 1
            if isinstance(node.type, ast.Name) and node.type.id == "Exception":
                if node.name is None:
                    bare += 1
                else:
                    bound += 1
    return bare, bound, total


def analyze_dir(directory: str) -> tuple[int, int, int]:
    bare, bound, total = 0, 0, 0
    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            b, bo, t = count_exceptions_in_file(path)
            bare += b
            bound += bo
            total += t
    return bare, bound, total


def main():
    base_path = "/Users/borjafernandezangulo/30_CORTEX"
    directories = ["cortex/engine", "cortex/memory", "cortex/swarm"]
    for d in directories:
        bare, bound, total = analyze_dir(os.path.join(base_path, d))
        print(f"{d}: {bare} bare, {bound} bound, {total} total")


if __name__ == "__main__":
    main()
