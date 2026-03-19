import asyncio
import time

from cortex.extensions.swarm.worktree_isolation import _git, isolated_worktree


async def benchmark():
    branch = "test/benchmark-v0.3.0"
    times = []

    print("🚀 Starting Worktree Isolation Benchmark (v0.3.0)")

    for i in range(3):
        t0 = time.monotonic()
        async with isolated_worktree(f"{branch}-{i}") as wt_path:
            t1 = time.monotonic()

            # Verify git config
            rc, stdout, _ = await _git("-C", str(wt_path), "config", "user.name")
            name = stdout.decode().strip()

            rc, stdout, _ = await _git("-C", str(wt_path), "config", "core.filemode")
            filemode = stdout.decode().strip()

            print(
                f"  Iteration {i}: Created in {(t1 - t0) * 1000:.1f}ms | User: {name} | FileMode: {filemode}"
            )

            times.append(t1 - t0)

        t2 = time.monotonic()
        print(f"  Iteration {i}: Destroyed in {(t2 - t1) * 1000:.1f}ms")

    avg = sum(times) / len(times)
    print(f"\n📊 Average Creation Latency: {avg * 1000:.1f}ms")


if __name__ == "__main__":
    asyncio.run(benchmark())
