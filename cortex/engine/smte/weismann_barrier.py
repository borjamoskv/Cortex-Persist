# [C5-REAL] Exergy-Maximized
"""
CORTEX - Weismann Barrier (Kernel Isolation Protocol)
Protects the CORTEX-Persist kernel from fatal mutations during autopoiesis.
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger("cortex.engine.smte.weismann")


def enforce_weismann_barrier(target_kernel_file: str, mutator_callback) -> bool:
    """
    Executes a mutation in an isolated somatic clone.
    Only overwrites the original kernel if the mutant survives the gauntlet.
    """
    original_path = Path(target_kernel_file).resolve()
    if not original_path.exists():
        logger.error(f"Kernel file {original_path} not found.")
        return False

    with tempfile.TemporaryDirectory(prefix="cortex_somatic_clone_") as clone_dir:
        clone_path = Path(clone_dir)

        # 1. Somatic Clone
        mutant_file = clone_path / original_path.name
        shutil.copy2(original_path, mutant_file)

        # 2. Mutate Clone
        # mutator_callback should read mutant_file, mutate, and write back to mutant_file
        logger.info(f"[WEISMANN] Injecting mutation into somatic clone: {mutant_file}")
        if mutator_callback is not None:
            success = mutator_callback(str(mutant_file))
        else:
            success = True

        if not success:
            logger.warning("[WEISMANN] Mutation failed to generate valid AST on clone.")
            return False

        # 3. Falsification (The Gauntlet)
        # We must prove the mutant can still parse/compile python code.
        # We create a dummy script and ask the mutant to parse it (if it's the parser).
        # To make it generic, we simply try to compile the mutant file as a module.
        logger.info("[WEISMANN] Running Ontological Falsification (Syntax/Compilation Check)...")
        import sys

        try:
            # We run it in a subprocess to prevent namespace poisoning or crashing the main process
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(mutant_file)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                logger.error(f"[WEISMANN] Mutant failed compilation!\n{result.stderr}")
                return False

        except Exception as e:
            logger.error(f"[WEISMANN] Gauntlet execution error: {e}")
            return False

        # 4. Hot-Swap (Crossover)
        logger.info("[WEISMANN] Mutant survived the gauntlet. Initiating Hot-Swap...")
        try:
            shutil.copy2(mutant_file, original_path)
            logger.info(
                f"[WEISMANN] SUCCESS: Kernel overwritten with superior mutation -> {original_path}"
            )
            return True
        except Exception as e:
            logger.error(f"[WEISMANN] Hot-Swap failed: {e}")
            return False
