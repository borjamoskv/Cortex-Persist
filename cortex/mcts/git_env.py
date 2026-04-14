"""MCTS Entorno de Simulación Git (Chronos).

Proporciona la interfaz determinista para bifurcar el multiverso CORTEX,
inyectar mutaciones, y simular la exergía termodinámica.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from pathlib import Path

from cortex.extensions.llm.router import CortexLLMRouter, CortexPrompt, IntentProfile

logger = logging.getLogger("cortex.mcts.git_env")


def _atomic_write_text(path: Path, content: str) -> None:
    """Persist mutations atomically to avoid leaving partial Chronos states."""
    target_dir = path.parent
    fd, temp_path = tempfile.mkstemp(prefix="chronos_", dir=target_dir, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(content)
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


class MCTSGitEnvironment:
    """Entorno Git Cuántico para el AlphaZero Autodidact."""

    def __init__(self, router: CortexLLMRouter, target_file: Path) -> None:
        self.router = router
        self.target_file = Path(target_file).absolute()
        if not self.target_file.exists():
            raise FileNotFoundError(f"Target file no existe: {self.target_file}")

    async def get_current_branch(self) -> str:
        """Devuelve el nombre de la rama actual."""
        proc = await asyncio.create_subprocess_exec(
            "git",
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip()

    async def branch_out(self, base_branch: str, new_node_id: str) -> str:
        """Bifurca el árbol de Git."""
        new_name = f"chronos/node-{new_node_id}"
        proc = await asyncio.create_subprocess_exec(
            "git",
            "checkout",
            "-b",
            new_name,
            base_branch,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        if proc.returncode != 0:
            # Fallback for existing branch
            fallback_proc = await asyncio.create_subprocess_exec(
                "git",
                "checkout",
                new_name,
            )
            await fallback_proc.communicate()
        return new_name

    async def mutate(self, prompt_instruction: str) -> bool:
        """Inyecta una mutación LLM en el archivo objetivo."""
        original_code = self.target_file.read_text(encoding="utf-8")

        prompt = CortexPrompt(
            system_instruction=(
                "You are CORTEX Chronos, the Quantum Software Architect. "
                "Mutate the following Python file strictly according to the task. "
                "Return ONLY the raw updated code. No markdown formatting if possible."
            ),
            working_memory=[
                {
                    "role": "user",
                    "content": f"Task: {prompt_instruction}\n\nCode:\n```python\n{original_code}\n```",
                }
            ],
            intent=IntentProfile.CODE,
            temperature=0.8,  # Alta temperatura para forzar divergencia evolutiva
            max_tokens=8192,
        )

        res = await self.router.execute_resilient(prompt)
        if res.is_err():
            logger.error("Error en mutación LLM: %s", res.error)
            return False

        new_code = res.unwrap().strip()
        # Clean markdown if present
        if new_code.startswith("```"):
            lines = new_code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            new_code = "\n".join(lines).strip()

        _atomic_write_text(self.target_file, new_code)
        logger.info("🧬 [CHRONOS] Archivo mutado: %s", self.target_file.name)
        return True

    async def simulate(self) -> float:
        """Juega el multiverso: Ejecuta pytest y calcula el Yield y Exergía.

        Reward Function:
        1.0 si pasa tests limpios,
        0.0 si rompe la integridad del sistema.
        (Futuro: multiplicar por eficiencia térmica/latencia).
        """
        logger.info("🧪 [CHRONOS] Ejecutando simulación de integridad (pytest)...")
        start_time = time.perf_counter()

        # Corremos la suite de pruebas completa o las reglas ruff para chequear syntax
        proc_ruff = await asyncio.create_subprocess_exec(
            "ruff",
            "check",
            str(self.target_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc_ruff.communicate()

        if proc_ruff.returncode != 0:
            logger.warning("💥 [CHRONOS] Mutación aniquilada: Invalida el linter estricto.")
            return 0.0

        proc_test = await asyncio.create_subprocess_exec(
            "pytest",
            "tests/",
            "-v",
            "-q",
            "--tb=no",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc_test.communicate()

        duration = time.perf_counter() - start_time

        if proc_test.returncode == 0:
            logger.info(
                "💎 [CHRONOS] Mutación termodinámicamente viable (Passed en %.2fs).", duration
            )
            # En la versión P0, es binario
            return 1.0
        else:
            logger.warning("💥 [CHRONOS] Mutación aniquilada: Falla aserción o causa regresión.")
            return 0.0

    async def secure_checkout(self, branch: str) -> None:
        """Vuelve a una rama segura restaurando cualquier cambio."""
        logger.debug("Restaurando entropía: checkout a %s", branch)
        await (
            await asyncio.create_subprocess_exec("git", "reset", "--hard", "HEAD")
        ).communicate()
        await (await asyncio.create_subprocess_exec("git", "clean", "-fd")).communicate()
        await (await asyncio.create_subprocess_exec("git", "checkout", branch)).communicate()
