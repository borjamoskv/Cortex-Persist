import asyncio
import logging
import os
import shutil
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

logger = logging.getLogger("cortex.extensions.swarm.worktree")


class WorktreeIsolationError(Exception):
    """Excepción específica O(1) para fallos críticos en el ciclo de vida del worktree."""

    pass


@asynccontextmanager
async def isolated_worktree(
    branch_name: str, base_path: str | Path | None = None
) -> AsyncGenerator[Path, None]:
    """
    Gestor O(1) de Workspaces aislados usando `git worktree`.
    Crea un worktree físico, cede el contexto (yield) y garantiza su destrucción termodinámica al salir.
    """
    if base_path is None:
        # Default to a safe area outside the core repo to avoid indexer pollution
        base_path = Path.home() / ".cortex" / "worktrees"

    base_dir = Path(base_path)
    base_dir.mkdir(parents=True, exist_ok=True)

    # Sanitizamos el nombre para el directorio físico
    safe_name = branch_name.replace("/", "_").replace("\\", "_")
    worktree_path = base_dir / f"wt_{safe_name}_{os.getpid()}"

    logger.info(
        "🌿 [WORKTREE ISOLATION] Bipartición del espacio-tiempo. Creando worktree en: %s (Branch: %s)",
        worktree_path,
        branch_name,
    )

    # 1. Crear el Worktree
    try:
        # Check if we are inside a git repo
        proc = await asyncio.create_subprocess_exec(
            "git",
            "rev-parse",
            "--is-inside-work-tree",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr_chk = await proc.communicate()

        if proc.returncode != 0:
            raise WorktreeIsolationError(
                f"No estamos en un repositorio Git válido. Imposible bifurcar: {stderr_chk.decode().strip()}"
            )

        # Add the worktree
        proc_add = await asyncio.create_subprocess_exec(
            "git",
            "worktree",
            "add",
            "-b",
            branch_name,
            str(worktree_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_add, stderr_add = await proc_add.communicate()

        if proc_add.returncode != 0 and b"already exists" not in stderr_add:
            raise WorktreeIsolationError(
                f"Colapso al instanciar Git Worktree: {stderr_add.decode().strip()}"
            )

    except Exception as e:  # noqa: BLE001
        logger.error("☠️ [WORKTREE ISOLATION] Fallo catastrófico de instanciación: %s", e)
        raise WorktreeIsolationError(f"Fallo de instanciación: {e}") from e

    # Extraemos el target original antes del yield
    cwd_original = Path.cwd()

    try:
        # 2. Ceder la ejecución al Agente (dentro de la burbuja termodinámica)
        # Nota: Idealmente CORTEX debería usar rutas absolutas, pero si un agente
        # asume que está en el root, podemos hacer un `os.chdir` temporal.
        # Preferimos sin embargo proveer la ruta para que la herramienta del Agente opere sobre ella.
        yield worktree_path

    finally:
        # 3. Aniquilación Estructural O(1) (Rolback determinista)
        logger.info(
            "🔥 [WORKTREE ISOLATION] Colapso de función de onda. Purgando worktree obsoleto: %s",
            worktree_path,
        )
        try:
            # Aseguramos que no estamos bloqueando el path
            if Path.cwd() == worktree_path or worktree_path in Path.cwd().parents:
                os.chdir(cwd_original)

            # Git exige removerlo de su índice interno primero
            proc_rm = await asyncio.create_subprocess_exec(
                "git",
                "worktree",
                "remove",
                "--force",
                str(worktree_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc_rm.communicate()

            # Limpieza forzada de ramas huérfanas si la directiva lo exige
            proc_branch = await asyncio.create_subprocess_exec(
                "git",
                "branch",
                "-D",
                branch_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc_branch.communicate()

            # Limpieza física si Git falló al borrar
            if worktree_path.exists():
                shutil.rmtree(worktree_path, ignore_errors=True)

            logger.info("✅ [WORKTREE ISOLATION] Purgatorio aniquilado. RAM recuperada.")

        except Exception as e:  # noqa: BLE001
            logger.error(
                "⚠️ [WORKTREE ISOLATION] Residuo termodinámico detectado al purgar %s: %s",
                worktree_path,
                e,
            )
