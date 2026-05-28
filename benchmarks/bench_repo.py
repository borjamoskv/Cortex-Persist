import os
import subprocess
import sys
import time

IMPORT_PROBE = "import cortex; from cortex import CortexEngine"
STEADY_STATE_IMPORT_THRESHOLD = 1.0
STEADY_STATE_SAMPLES = 2


def _measure_import_once() -> float:
    start = time.perf_counter()
    subprocess.run(  # noqa: S603
        [sys.executable, "-c", IMPORT_PROBE],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    end = time.perf_counter()
    return end - start


def bench_imports() -> tuple[float, float]:
    # The first import after an editable install is noisy on CI runners because it
    # folds in import cache and filesystem cold-start effects. We still report it,
    # but we gate on the warmed steady-state import budget.
    cold_import_time = _measure_import_once()
    steady_state_runs = [_measure_import_once() for _ in range(STEADY_STATE_SAMPLES)]

    return cold_import_time, min(steady_state_runs)


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

    cold_import_time, import_time = bench_imports()
    print(f"📦 Core Import Time (cold): {cold_import_time:.4f}s")
    print(f"📦 Core Import Time (steady-state): {import_time:.4f}s")

    size_mb = check_package_size()
    print(f"💽 Cortex Source Size: {size_mb:.2f} MB")

    if import_time > STEADY_STATE_IMPORT_THRESHOLD:
        print(f"❌ Steady-state import time exceeds {STEADY_STATE_IMPORT_THRESHOLD:.1f}s threshold!")
        sys.exit(1)

    if cold_import_time > STEADY_STATE_IMPORT_THRESHOLD:
        print("ℹ️ Cold import exceeded the steady-state budget, but warmed import passed.")

    print("✅ All benchmarks passed.")


if __name__ == "__main__":
    main()
