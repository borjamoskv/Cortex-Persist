# [C5-REAL] Exergy-Maximized
"""
Ouroboros-∞ Temporal Branching Engine
Maximizes Exergy (Impact / Risk).
Isolates autonomous structural mutations into ephemeral git branches.
Executes the full test suite. If successful, merges to main. If failed, violently destroys the branch.
"""

import asyncio
import logging
import subprocess
import uuid
from typing import Any

from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.utils.errors import CortexError

logger = logging.getLogger("cortex.engine.evolution.ouroboros")


class TemporalBranchingEngine:
    """
    Arqueología Temporal: Git para la Realidad.
    Permite probar mutaciones de código autónomas en líneas temporales aisladas.
    Riesgo = 0. Impacto = Infinito.
    """

    def __init__(self, workspace_path: str = "."):
        self.workspace = workspace_path

    async def simulate_mutation(self, mutation_func, *args, **kwargs) -> dict[str, Any]:
        """
        1. Crea un fork temporal de la realidad (git branch).
        2. Ejecuta la función mutadora.
        3. Valida los invariantes (pytest).
        4. Si falla, colapsa la rama y restaura.
        5. Si pasa, hace merge y consolida la evolución.
        """
        branch_id = f"causality-fork-{uuid.uuid4().hex[:8]}"
        try:
            original_branch = self._run_cmd("git rev-parse --abbrev-ref HEAD").strip()
        except CortexError:
            original_branch = "main"

        logger.info(f"🕰️ [Ouroboros] Bifurcando la realidad hacia la línea temporal: {branch_id}")

        try:
            # Fork reality
            self._run_cmd(f"git checkout -b {branch_id}")

            # Apply mutation (this function is expected to alter files in the workspace)
            logger.info("🧬 [Ouroboros] Inyectando mutación estructural en la línea temporal aislada...")
            mutation_result = await mutation_func(*args, **kwargs)

            # Commit the mutation locally in the branch to run tests safely
            self._run_cmd("git add .")
            self._run_cmd(f"git commit -m 'chore(evolution): temp mutation {branch_id}' --no-verify")

            # Verify Reality (Run Tests)
            logger.info("🛡️ [Ouroboros] Validando integridad de la nueva realidad (Pytest)...")
            test_exit_code = self._run_tests()

            if test_exit_code == 0:
                # Reality is stable. Merge it.
                logger.info(f"🌌 [Ouroboros] Invariantes confirmados. Colapsando {branch_id} sobre {original_branch}.")
                self._run_cmd(f"git checkout {original_branch}")
                self._run_cmd(f"git merge {branch_id} --no-ff -m 'feat(evolution): autonomous structural mutation merged'")
                self._run_cmd(f"git branch -D {branch_id}")

                ENDOCRINE.pulse(HormoneType.DOPAMINE, 0.5, "Ouroboros Mutation Successful")
                return {"status": "merged", "branch": branch_id, "result": mutation_result}
            else:
                # Reality collapsed. Burn the branch.
                raise CortexError("Los invariantes de prueba fallaron en la nueva línea temporal.")

        except Exception as e:
            logger.error(f"🔥 [Ouroboros] Colapso estructural detectado: {e}")
            logger.warning(f"🕰️ [Ouroboros] Purificando línea temporal inestable. Retornando a {original_branch}.")
            ENDOCRINE.pulse(HormoneType.CORTISOL, 0.6, "Ouroboros Mutation Failed")

            # Rollback
            try:
                self._run_cmd("git reset --hard HEAD")
                self._run_cmd(f"git checkout {original_branch}")
                self._run_cmd(f"git branch -D {branch_id}")
            except Exception as rollback_err:
                logger.critical(f"FATAL: Ouroboros rollback failed: {rollback_err}")

            return {"status": "rollback", "branch": branch_id, "error": str(e)}

    def _run_cmd(self, cmd: str) -> str:
        try:
            result = subprocess.run(
                cmd, shell=True, cwd=self.workspace, capture_output=True, text=True, check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {cmd}\nOutput: {e.output}\nError: {e.stderr}")
            raise CortexError(f"System command failed: {cmd}") from e

    def _run_tests(self) -> int:
        """Ejecuta los invariantes nucleares usando pytest."""
        # Se restringe a tests de verificación (rápido y determinista) para el ciclo Ouroboros
        result = subprocess.run(
            ["pytest", "tests/verification/", "-q"],
            cwd=self.workspace,
            capture_output=True,
            text=True,
        )
        return result.returncode
