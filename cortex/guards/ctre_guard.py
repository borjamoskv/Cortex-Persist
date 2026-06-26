"""
C5-REAL CTRE (Commit-Time Reconciliation Engine) Guardian.
Prevents TOCTOU vulnerabilities in UI agents and Concurrent State execution.
"""

import logging

logger = logging.getLogger(__name__)


class CTRECollisionError(RuntimeError):
    """Raised when an atomic commit fails due to a TOCTOU collision."""

    def __init__(self, expected: int, current: int, epsilon: int):
        super().__init__(
            f"CTRE SAGA ABORT: UI TOCTOU Collision (Epsilon: {epsilon}µs). Expected {expected}, got {current}."
        )
        self.epsilon = epsilon
        self.expected_hash = expected
        self.current_hash = current


# Fallback in case cortex_rs is not compiled
try:
    import cortex_rs

    HAS_RUST_CTRE = True
except ImportError:
    HAS_RUST_CTRE = False


class CTREGuard:
    """
    Motor CTRE para CORTEX Persist.
    Implementa concurrencia optimista mediante Test-and-Set atómico delegado a Rust.
    """

    @staticmethod
    def validate_commit(
        expected_hash: int, current_hash: int, target_x: float = 0.0, target_y: float = 0.0
    ) -> tuple[bool, int]:
        """
        Ejecuta la verificación atómica (isomorfismo de estado).

        Args:
            expected_hash: Hash de estado cuando el Agente (VLM/LLM) planificó la acción (t0).
            current_hash: Hash de estado microscópicamente anterior a la inyección (t1).
            target_x: Coordenada X (para UI agents).
            target_y: Coordenada Y (para UI agents).

        Returns:
            Tuple[bool, int]: (True si el commit es exitoso / False si hay divergencia TOCTOU, tiempo en microsegundos epsilon)
        """
        if HAS_RUST_CTRE and hasattr(cortex_rs, "ctre_atomic_commit"):
            # Ejecución C5-REAL vía FFI
            try:
                success, epsilon_us = getattr(cortex_rs, "ctre_atomic_commit")(  # noqa: B009
                    expected_hash, target_x, target_y, current_hash
                )
                if not success:
                    logger.warning(
                        f"[CTRE] SAGA ABORT: Mutación detectada (TOCTOU). Epsilon={epsilon_us}µs"
                    )
                else:
                    logger.info(
                        f"[CTRE] COMMIT SUCCESS: Isomorfismo estructural verificado en {epsilon_us}µs"
                    )
                return success, epsilon_us
            except (ValueError, TypeError, KeyError, AssertionError) as e:
                logger.error(f"[CTRE] FFI Error en validación atómica: {e}")
                # Fallback on error
                return CTREGuard._python_fallback(expected_hash, current_hash)
        else:
            # Fallback a Python GIL (propenso a Jitter)
            return CTREGuard._python_fallback(expected_hash, current_hash)

    @staticmethod
    def _python_fallback(expected_hash: int, current_hash: int) -> tuple[bool, int]:
        import time

        t_start = time.perf_counter_ns()
        success = expected_hash == current_hash
        epsilon_us = (time.perf_counter_ns() - t_start) // 1000

        if not success:
            logger.warning(
                f"[CTRE-PY] SAGA ABORT (GIL Warning): Mutación detectada. Epsilon={epsilon_us}µs"
            )
        return success, epsilon_us
