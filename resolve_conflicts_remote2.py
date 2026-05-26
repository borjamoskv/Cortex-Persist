import re
import sys
from pathlib import Path


def resolve_file(path: Path) -> int:
    content = path.read_text(encoding="utf-8", errors="replace")

    # We want to replace the whole block starting with <<<<<<< HEAD and ending with >>>>>>> something
    # with just the REMOTE block
    resolved, count = re.subn(
        r"<<<<<<< HEAD.*?\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n?", r"\2", content, flags=re.DOTALL
    )

    if count > 0:
        path.write_text(resolved, encoding="utf-8")
    return count


def main():
    root = Path("cortex")
    files = sorted(root.rglob("*.py"))

    total_conflicts = 0
    total_files = 0

    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "<<<<<<< HEAD" not in content:
            continue
        count = resolve_file(f)
        if count > 0:
            total_files += 1
            total_conflicts += count
            print(f"[FIX] {f} — {count} conflicts resolved with REMOTE")

    print(f"\nRESOLVED: {total_conflicts} conflicts in {total_files} files")


if __name__ == "__main__":
    main()
