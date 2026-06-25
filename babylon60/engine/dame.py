# [C5-REAL] Framework DAME (Diseño de Acciones de Máxima Exergía)
# Anchored: cortex/engine/dame.py
# Creator: Borja Moskv (borjamoskv)

import asyncio
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("babylon60.engine.dame")

class DAMEError(Exception):
    """Excepción base del Framework DAME."""
    pass

class DAMEApoptosisError(DAMEError):
    """Detonada por exceder los límites físicos de reintentos sin validación (DAME-008)."""
    pass

class DAMEState:
    """
    DAME-001 (External Memory Persistence)
    Gestiona la persistencia física del estado cognitivo de la sesión en almacenamiento externo.
    """
    def __init__(self, state_file_path: Path):
        self.state_file_path = Path(state_file_path)
        self.state: dict[str, Any] = {}
        self.load()

    def load(self) -> dict[str, Any]:
        if self.state_file_path.exists():
            try:
                with open(self.state_file_path, encoding="utf-8") as f:
                    self.state = json.load(f)
                logger.info(f"[DAME-001] Estado cargado con éxito desde {self.state_file_path}")
            except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as e:  # P0-PURGED
                logger.error(f"[DAME-001] Error leyendo estado externo: {e}")
                self.state = {}
        else:
            self.state = {}
        return self.state

    def save(self) -> None:
        try:
            self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
            logger.info(f"[DAME-001] Estado guardado en {self.state_file_path}")
        except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as e:  # P0-PURGED
            logger.error(f"[DAME-001] Error guardando estado externo: {e}")
            raise DAMEError(f"Fallo de persistencia física: {e}")

    def update(self, key: str, value: Any) -> None:
        self.state[key] = value
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)


class DAMEExecutor:
    """
    DAME-002 (Deterministic Exit Condition)
    DAME-008 (Limit-Bounded Retry Apoptosis)
    DAME-009 (Asynchronous Log Containment)
    Ejecuta mutaciones de estado y exige condiciones lógicas de éxito mediante validadores externos.
    """
    def __init__(self, state: DAMEState, max_retries: int = 5):
        self.state = state
        self.max_retries = max_retries

    async def execute_with_assertion(
        self,
        task_id: str,
        execution_coro: Callable[[], Any],
        validation_script_path: Path,
        args: Optional[list[str]] = None
    ) -> bool:
        """
        Ejecuta el payload de mutación y asume aserción binaria rígida mediante validador físico.
        """
        retry_key = f"retry_count_{task_id}"
        current_retries = self.state.get(retry_key, 0)

        if current_retries >= self.max_retries:
            logger.error(f"[DAME-008] Apoptosis por Inercia Entrópica detonada para {task_id}. Retries: {current_retries}")
            raise DAMEApoptosisError(f"Se excedió el límite de reintentos ({self.max_retries}) sin satisfacer la meta verificable.")

        logger.info(f"Ejecutando paso de tarea {task_id} (Intento {current_retries + 1}/{self.max_retries})")
        
        # Ejecutar payload
        if asyncio.iscoroutinefunction(execution_coro):
            await execution_coro()
        else:
            execution_coro()

        # DAME-002: Meta Verificable
        # Ejecutar validador externo y comprobar código de retorno 0
        args_list = args or []
        log_file = Path(f"/tmp/dame_{task_id}_validate_{current_retries}.log")
        
        logger.info(f"[DAME-009] Redirigiendo logs de validación a {log_file}")
        
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                proc = await asyncio.create_subprocess_exec(
                    str(validation_script_path),
                    *args_list,
                    stdout=f,
                    stderr=f
                )
                exit_code = await proc.wait()

            if exit_code == 0:
                logger.info(f"[DAME-002] Meta verificada con éxito para {task_id} (exit code 0).")
                self.state.update(retry_key, 0)
                self.state.update(f"status_{task_id}", "COMPLETED")
                return True
            else:
                logger.warning(f"[DAME-002] Fallo de meta para {task_id} (exit code {exit_code}).")
                self.state.update(retry_key, current_retries + 1)
                return False

        except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as e:  # P0-PURGED
            logger.error(f"Error ejecutando validador: {e}")
            self.state.update(retry_key, current_retries + 1)
            return False


class DAMEAsyncDelegator:
    """
    DAME-003 (Decoupled Async Delegation)
    Orquesta procesos secundarios concurrentes y desacoplados.
    """
    @staticmethod
    async def delegate_task(
        task_id: str,
        cmd: list[str],
        log_dir: Path = Path("/tmp/dame_async_logs")
    ) -> asyncio.Task:
        """
        Dispara una tarea asíncrona secundaria con logs contenidos en disco físico.
        """
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{task_id}.log"
        
        async def _run():
            logger.info(f"[DAME-003] Delegando tarea asíncrona {task_id} -> Logs en {log_path}")
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=f,
                        stderr=f
                    )
                    exit_code = await proc.wait()
                if exit_code == 0:
                    logger.info(f"[DAME-003] Tarea delegada {task_id} finalizada exitosamente.")
                else:
                    logger.warning(f"[DAME-003] Tarea delegada {task_id} finalizó con error (code {exit_code}).")
            except (ValueError, TypeError, KeyError, RuntimeError, ConnectionError, OSError) as e:  # P0-PURGED
                logger.error(f"[DAME-003] Error ejecutando tarea delegada {task_id}: {e}")

        return asyncio.create_task(_run())
