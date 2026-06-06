#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from cortex.engine.smte.ouroboros_compiler import OuroborosCompiler


async def main():
    sys.stdout.write("=== [ AGENTS.ARCHI ] Ouroboros-Omega Live Loop ===\n")
    sys.stdout.write("\n[1] Invoking L-EPI Guard Compiler...\n")

    target_file = root_dir / "scripts" / "claude_stress_test.py"

    compiler = OuroborosCompiler()

    # We run the compiler against the stress test script to see the new metrics
    result = await compiler.compile_entity(target_file)

    if result:
        sys.stdout.write("\n[2] Compilation/Amputation cycle complete.\n")
    else:
        sys.stdout.write("\n[2] SMTE LOOP ABORTED.\n")


if __name__ == "__main__":
    asyncio.run(main())
