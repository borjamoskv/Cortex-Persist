import os
import sys
import time


def bench_imports() -> float:
    start = time.perf_counter()
    import cortex  # noqa: F401
    from cortex import CortexEngine  # noqa: F401

    end = time.perf_counter()
    return end - start


def check_package_size() -> float:
    total_size = 0
    cortex_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cortex"))
    for dirpath, _, filenames in os.walk(cortex_dir):
        if "__pycache__" in dirpath:
            continue
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024)


def main() -> None:
    quick_mode = "--quick" in sys.argv
    label = " (QUICK)" if quick_mode else ""
    print(f"🚀 Running Repository Benchmarks...{label}")

    import_time = bench_imports()
    print(f"📦 Core Import Time: {import_time:.4f}s")

    size_mb = check_package_size()
    print(f"💽 Cortex Source Size: {size_mb:.2f} MB")

    if import_time > 1.0:
        print("❌ Import time exceeds 1.0s threshold!")
        sys.exit(1)

    print("✅ All benchmarks passed.")


if __name__ == "__main__":
    main()
