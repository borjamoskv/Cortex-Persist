import asyncio
import logging
import os
import shutil
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger("cortex.extensions.swarm.worktree")


class WorktreeIsolationError(Exception):
    """Excepción específica O(1) para fallos críticos en el ciclo de vida del worktree."""

    pass


async def _run_git_with_backoff(
    *args: str, max_retries: int = 5, backoff_factor: float = 0.5
) -> tuple[int, bytes, bytes]:
    """Ejecuta un comando Git con backoff exponencial. Inmune a index.lock temporales."""
    for attempt in range(max_retries):
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        # lock file detection
        if proc.returncode != 0 and b"index.lock" in stderr:
            wait_time = backoff_factor * (2**attempt)
            logger.warning(
                "🔒 [WORKTREE IMMUNITY] Git index locked. Retrying in %.2fs (Attempt %d/%d)",
                wait_time,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(wait_time)
            continue

        return proc.returncode, stdout, stderr

    raise WorktreeIsolationError(
        "Colapso termodinámico: Incapaz de superar el bloqueo lock"
        f" (index.lock) tras {max_retries} intentos."
    )


def _purge_zombies(base_dir: Path) -> None:
    """Aniquila worktrees huérfanos de ejecuciones previas anómalas (Ghosts)."""
    if not base_dir.exists():
        return

    try:
        current_pid = os.getpid()
        for path in base_dir.iterdir():
            if path.is_dir() and path.name.startswith("wt_"):
                parts = path.name.split("_")
                try:
                    pid = int(parts[-2])  # Expected format: wt_branch_PID_UUID
                    if pid != current_pid:
                        # Simple detection: if the process is not alive
                        try:
                            os.kill(pid, 0)
                        except OSError:
                            # Process is dead, worktree is a ghost
                            logger.info(
                                "👻 [WORKTREE IMMUNITY] Purgando worktree fantasma: %s", path
                            )
                            shutil.rmtree(path, ignore_errors=True)
                except (ValueError, IndexError):
                    # Fallback structural purge if format is unknown
                    pass
    except Exception as e:
        logger.warning("⚠️ [WORKTREE IMMUNITY] Fallo menor al purgar zombies: %s", e)


@asynccontextmanager
async def isolated_worktree(
    branch_name: str,
    base_path: Optional[Union[str, Path]] = None,
    force_unique_branch: bool = False,
) -> AsyncGenerator[Path, None]:
    """
    Gestor O(1) de Workspaces aislados usando `git worktree`.
    Crea un worktree físico, cede el contexto (yield) y garantiza
    su destrucción termodinámica al salir.
    """
    if base_path is None:
        # Default to a safe area outside the core repo to avoid indexer pollution
        base_path = Path.home() / ".cortex" / "worktrees"

    base_dir = Path(base_path)
    base_dir.mkdir(parents=True, exist_ok=True)

    # Immune system purge
    _purge_zombies(base_dir)

    # Sanitizamos el nombre para el directorio físico
    safe_name = branch_name.replace("/", "_").replace("\\", "_")
    unique_id = uuid.uuid4().hex[:8]
    worktree_path = base_dir / f"wt_{safe_name}_{os.getpid()}_{unique_id}"

    # Determine isolated branch name
    actual_branch = f"{branch_name}-{unique_id}" if force_unique_branch else branch_name

    logger.info(
        "🌿 [WORKTREE ISOLATION] Bipartición del espacio-tiempo."
        " Creando worktree en: %s (Branch: %s)",
        worktree_path,
        actual_branch,
    )

    # 1. Crear el Worktree
    try:
        # Check if we are inside a git repo
        code, stdout, stderr = await _run_git_with_backoff("rev-parse", "--is-inside-work-tree")

        if code != 0:
            raise WorktreeIsolationError(
                "No estamos en un repositorio Git válido."
                f" Imposible bifurcar: {stderr.decode().strip()}"
            )

        # Attempt to checkout existing or create new branch
        code_add, stdout_add, stderr_add = await _run_git_with_backoff(
            "worktree", "add", str(worktree_path), actual_branch
        )

        if code_add != 0:
            if b"already exists" in stderr_add or b"invalid reference" in stderr_add:
                # Si falla porque la rama no existe, creémosla desde el punto actual (HEAD)
                code_b, stdout_b, stderr_b = await _run_git_with_backoff(
                    "worktree", "add", "-b", actual_branch, str(worktree_path)
                )
                if code_b != 0 and b"already exists" not in stderr_b:
                    raise WorktreeIsolationError(
                        f"Colapso al instanciar Git Worktree (-b): {stderr_b.decode().strip()}"
                    )
            else:
                raise WorktreeIsolationError(
                    f"Colapso al instanciar Git Worktree: {stderr_add.decode().strip()}"
                )

    except Exception as e:
        logger.error("☠️ [WORKTREE ISOLATION] Fallo catastrófico de instanciación: %s", e)
        raise WorktreeIsolationError(f"Fallo de instanciación: {e}") from e

    # Extraemos el target original antes del yield
    cwd_original = Path.cwd()

    try:
        # 2. Ceder la ejecución al Agente (dentro de la burbuja termodinámica)
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
            await _run_git_with_backoff("worktree", "remove", "--force", str(worktree_path))

            # Si forzamos una rama única, se podría borrar.
            # De lo contrario la conservamos intacta.
            if force_unique_branch:
                await _run_git_with_backoff("branch", "-D", actual_branch)

            # Limpieza física si Git falló al borrar
            if worktree_path.exists():
                shutil.rmtree(worktree_path, ignore_errors=True)

            logger.info(
                "✅ [WORKTREE ISOLATION] Purgatorio aniquilado."
                " RAM y estado Git recuperados sin ghosting."
            )

        except Exception as e:
            logger.error(
                "⚠️ [WORKTREE ISOLATION] Residuo termodinámico detectado al purgar %s: %s",
                worktree_path,
                e,
            )
