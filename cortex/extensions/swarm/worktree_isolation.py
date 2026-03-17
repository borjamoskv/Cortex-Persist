<<<<<<< HEAD
"""Worktree Isolation — O(1) ephemeral workspace lifecycle.

Creates, yields, and deterministically destroys git worktrees
with full signal telemetry and timeout protection.
"""

from __future__ import annotations

=======
>>>>>>> origin/main
import asyncio
import logging
import os
import shutil
<<<<<<< HEAD
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.extensions.swarm.worktree")

# ── Constants ─────────────────────────────────────────────────────────

GIT_CMD_TIMEOUT: float = 30.0  # seconds per git subprocess
WORKTREE_DIR_PREFIX: str = "wt_"


# ── Signal Emission ──────────────────────────────────────────────────


def _base_payload(
    branch: str,
    path: str,
    **extra: Any,
) -> dict[str, Any]:
    """Build a canonical signal payload. DRY across all emission points."""
    payload: dict[str, Any] = {
        "branch": branch,
        "path": path,
        "pid": os.getpid(),
        "timestamp": time.time(),
    }
    payload.update(extra)
    return payload


def _emit_worktree_signal(
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Fire-and-forget signal emission. Never blocks, never raises."""
    try:
        from cortex.database.core import connect as db_connect
        from cortex.extensions.signals.bus import SignalBus

        db_path = os.environ.get("CORTEX_DB_PATH")
        if not db_path:
            return
        conn = db_connect(db_path, timeout=2)
        try:
            bus = SignalBus(conn)
            bus.emit(
                event_type,
                payload,
                source="worktree_isolation",
                project="CORTEX_SWARM",
            )
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        logger.debug(
            "Worktree signal emission failed for %s",
            event_type,
        )


# ── Error Type ───────────────────────────────────────────────────────


class WorktreeIsolationError(Exception):
    """Critical lifecycle failure in worktree isolation."""


# ── Git Subprocess Helper ────────────────────────────────────────────


async def _git(
    *args: str,
    timeout: float = GIT_CMD_TIMEOUT,
) -> tuple[int, bytes, bytes]:
    """Run a git command with timeout protection.

    Returns (returncode, stdout, stderr).
    Raises WorktreeIsolationError on timeout.
    """
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise WorktreeIsolationError(f"git {args[0]} timed out after {timeout}s") from None
    return proc.returncode, stdout, stderr


# ── Core Context Manager ─────────────────────────────────────────────
=======
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

logger = logging.getLogger("cortex.extensions.swarm.worktree")


class WorktreeIsolationError(Exception):
    """Excepción específica O(1) para fallos críticos en el ciclo de vida del worktree."""

    pass
>>>>>>> origin/main


@asynccontextmanager
async def isolated_worktree(
<<<<<<< HEAD
    branch_name: str,
    base_path: str | Path | None = None,
) -> AsyncGenerator[Path, None]:
    """O(1) ephemeral workspace via `git worktree`.

    Creates a physical worktree, yields control, and guarantees
    deterministic destruction on exit — regardless of success or
    failure inside the yielded block.

    Signals emitted:
        worktree:created          — after successful creation
        worktree:isolation_failed — on creation failure
        worktree:destroyed        — after clean teardown
        worktree:residue_detected — if teardown left artifacts
    """
    if base_path is None:
=======
    branch_name: str, base_path: Optional[str | Path] = None
) -> AsyncGenerator[Path, None]:
    """
    Gestor O(1) de Workspaces aislados usando `git worktree`.
    Crea un worktree físico, cede el contexto (yield) y garantiza su destrucción termodinámica al salir.
    """
    if base_path is None:
        # Default to a safe area outside the core repo to avoid indexer pollution
>>>>>>> origin/main
        base_path = Path.home() / ".cortex" / "worktrees"

    base_dir = Path(base_path)
    base_dir.mkdir(parents=True, exist_ok=True)

<<<<<<< HEAD
    safe_name = branch_name.replace("/", "_").replace("\\", "_")
    worktree_path = base_dir / f"{WORKTREE_DIR_PREFIX}{safe_name}_{os.getpid()}"

    def _payload(**extra: Any) -> dict[str, Any]:
        return _base_payload(branch_name, str(worktree_path), **extra)

    logger.info(
        "[WORKTREE] Creating: %s (branch: %s)",
=======
    # Sanitizamos el nombre para el directorio físico
    safe_name = branch_name.replace("/", "_").replace("\\", "_")
    worktree_path = base_dir / f"wt_{safe_name}_{os.getpid()}"

    logger.info(
        "🌿 [WORKTREE ISOLATION] Bipartición del espacio-tiempo. Creando worktree en: %s (Branch: %s)",
>>>>>>> origin/main
        worktree_path,
        branch_name,
    )

<<<<<<< HEAD
    t0 = time.monotonic()

    # ── Phase 1: Creation ─────────────────────────────────────────
    try:
        rc, _, stderr = await _git(
            "rev-parse",
            "--is-inside-work-tree",
        )
        if rc != 0:
            raise WorktreeIsolationError(f"Not inside a valid Git repo: {stderr.decode().strip()}")

        # Try creating branch; if it already exists, checkout instead
        rc, _, stderr = await _git(
=======
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
>>>>>>> origin/main
            "worktree",
            "add",
            "-b",
            branch_name,
            str(worktree_path),
<<<<<<< HEAD
        )
        if rc != 0:
            if b"already exists" in stderr:
                # Branch exists — attach without -b
                # (Ω₂ Infrastructure Refinement)
                rc2, _, stderr2 = await _git(
                    "worktree",
                    "add",
                    str(worktree_path),
                    branch_name,
                )
                if rc2 != 0:
                    _emit_worktree_signal(
                        "worktree:isolation_failed",
                        _payload(error=stderr2.decode().strip()),
                    )
                    error_msg = f"Worktree add failed: {stderr2.decode().strip()}"
                    raise WorktreeIsolationError(error_msg)
            else:
                _emit_worktree_signal(
                    "worktree:isolation_failed",
                    _payload(error=stderr.decode().strip()),
                )
                error_msg = f"Worktree add failed: {stderr.decode().strip()}"
                raise WorktreeIsolationError(error_msg)

        # ── Phase 1.5: Git Configuration ──────────────────────────
        # Ensure the isolated environment has a valid user and other basics
        # to prevent agent operations from failing.
        await _git("-C", str(worktree_path), "config", "user.name", "CORTEX Agent")
        await _git("-C", str(worktree_path), "config", "user.email", "agent@cortex.persist")
        # Optimization: skip index/worktree comparison for performance if needed
        await _git("-C", str(worktree_path), "config", "core.filemode", "false")

    except WorktreeIsolationError:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("[WORKTREE] Creation failed: %s", e)
        _emit_worktree_signal(
            "worktree:isolation_failed",
            _payload(error=str(e)),
        )
        raise WorktreeIsolationError(f"Creation failed: {e}") from e

    creation_ms = (time.monotonic() - t0) * 1000
    cwd_original = Path.cwd()

    _emit_worktree_signal(
        "worktree:created",
        _payload(creation_ms=round(creation_ms, 1)),
    )

    # ── Phase 2: Yield to Agent ───────────────────────────────────
    try:
        yield worktree_path

    finally:
        # ── Phase 3: Deterministic Destruction ────────────────────
        t1 = time.monotonic()
        logger.info("[WORKTREE] Destroying: %s", worktree_path)

        try:
            # Restore cwd if we're inside the doomed path
            try:
                if Path.cwd() == worktree_path or worktree_path in Path.cwd().parents:
                    os.chdir(cwd_original)
            except OSError:
                os.chdir(cwd_original)

            # Remove from git index
            await _git(
=======
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
>>>>>>> origin/main
                "worktree",
                "remove",
                "--force",
                str(worktree_path),
<<<<<<< HEAD
            )

            # Delete orphan branch
            await _git("branch", "-D", branch_name)

            # Physical cleanup if git left residue
            if worktree_path.exists():
                shutil.rmtree(worktree_path, ignore_errors=True)

            teardown_ms = (time.monotonic() - t1) * 1000

            if worktree_path.exists():
                _emit_worktree_signal(
                    "worktree:residue_detected",
                    _payload(teardown_ms=round(teardown_ms, 1)),
                )
                logger.warning(
                    "[WORKTREE] Residue persists at %s",
                    worktree_path,
                )
            else:
                _emit_worktree_signal(
                    "worktree:destroyed",
                    _payload(
                        teardown_ms=round(teardown_ms, 1),
                        total_ms=round(
                            (time.monotonic() - t0) * 1000,
                            1,
                        ),
                    ),
                )
                logger.info(
                    "[WORKTREE] Destroyed in %.1fms",
                    teardown_ms,
                )

        except Exception as e:  # noqa: BLE001
            teardown_ms = (time.monotonic() - t1) * 1000
            logger.error(
                "[WORKTREE] Teardown error at %s: %s",
                worktree_path,
                e,
            )
            _emit_worktree_signal(
                "worktree:residue_detected",
                _payload(
                    error=str(e),
                    teardown_ms=round(teardown_ms, 1),
                ),
            )


async def cleanup_all_worktrees(base_path: str | Path | None = None) -> int:
    """Force-remove all ephemeral worktrees and their git metadata.

    Returns:
        Number of worktrees removed.
    """
    if base_path is None:
        base_path = Path.home() / ".cortex" / "worktrees"

    base_dir = Path(base_path)
    if not base_dir.exists():
        return 0

    count = 0
    # List all worktrees according to git
    rc, stdout, _ = await _git("worktree", "list", "--porcelain")
    if rc != 0:
        return 0

    lines = stdout.decode().splitlines()
    worktree_paths = [line[10:] for line in lines if line.startswith("worktree ")]

    for path_str in worktree_paths:
        path = Path(path_str)
        if path.name.startswith(WORKTREE_DIR_PREFIX):
            logger.info("[WORKTREE] Force cleaning: %s", path)
            await _git("worktree", "remove", "--force", path_str)
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
            count += 1

    return count
=======
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
>>>>>>> origin/main
