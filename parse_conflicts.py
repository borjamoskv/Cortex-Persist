import re


def show_conflicts(filepath):
    with open(filepath) as f:
        content = f.read()

    parts = re.split(
        r"<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> [a-f0-9]+.*?\n", content, flags=re.DOTALL
    )

    if len(parts) > 1:
        print(f"\n--- Conflicts in {filepath} ---")
        for i in range(1, len(parts), 3):
            print(f"Conflict {(i - 1) // 3 + 1}:")
            print("HEAD:")
            print(parts[i].strip())
            print("-" * 20)
            print("REMOTE:")
            print(parts[i + 1].strip())
            print("=" * 40)


show_conflicts("/Users/borjafernandezangulo/30_CORTEX/cortex/engine/__init__.py")
show_conflicts("/Users/borjafernandezangulo/30_CORTEX/cortex/engine/mutation_engine.py")
show_conflicts("/Users/borjafernandezangulo/30_CORTEX/cortex/memory/memory_archaeology.py")
