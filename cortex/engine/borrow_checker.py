import asyncio
import time


class StateDriftError(Exception):
    """Excepción lanzada cuando se violan las reglas de Borrowing (ej: doble &mut)."""
    pass

class LogicalBorrowChecker:
    """
    [C5-REAL] Logical Borrow Checker.
    Inspirado en el Ownership Model de Rust.
    Previene "Semantic Race Conditions" (corrupción de estado lógico) garantizando:
    - Múltiples préstamos inmutables (&State) simultáneos permitidos.
    - O un único préstamo mutable (&mut State) sin otros préstamos simultáneos.
    """
    def __init__(self):
        # Mapeo de namespace -> contador de préstamos inmutables activos
        self._shared_borrows: dict[str, int] = {}
        # Conjunto de namespaces con un préstamo mutable activo
        self._mut_borrows: set[str] = set()
        self._lock = asyncio.Lock()

    async def acquire_mut(self, namespace: str, timeout_sec: float = 5.0) -> bool:
        """Adquiere un préstamo mutable (&mut). Falla si hay cualquier otro préstamo."""
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            async with self._lock:
                if namespace not in self._mut_borrows and self._shared_borrows.get(namespace, 0) == 0:
                    self._mut_borrows.add(namespace)
                    return True
            await asyncio.sleep(0.01)
        raise StateDriftError(f"BorrowChecker: No se pudo adquirir '&mut {namespace}'. Violación de Exclusividad.")

    async def release_mut(self, namespace: str):
        """Libera el préstamo mutable."""
        async with self._lock:
            if namespace in self._mut_borrows:
                self._mut_borrows.remove(namespace)

    async def acquire_shared(self, namespace: str, timeout_sec: float = 5.0) -> bool:
        """Adquiere un préstamo inmutable (&). Falla si hay un préstamo mutable activo."""
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            async with self._lock:
                if namespace not in self._mut_borrows:
                    self._shared_borrows[namespace] = self._shared_borrows.get(namespace, 0) + 1
                    return True
            await asyncio.sleep(0.01)
        raise StateDriftError(f"BorrowChecker: No se pudo adquirir '& {namespace}'. Existe un '&mut' activo.")

    async def release_shared(self, namespace: str):
        """Libera un préstamo inmutable."""
        async with self._lock:
            if self._shared_borrows.get(namespace, 0) > 0:
                self._shared_borrows[namespace] -= 1
                if self._shared_borrows[namespace] == 0:
                    del self._shared_borrows[namespace]
