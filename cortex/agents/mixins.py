# [C5-REAL] Exergy-Maximized
from typing import Any


class EngineAwareMixin:
    """Sovereign Mixin para consolidar la inicialización del motor CORTEX."""

    _engine: Any
    _db_path: Any

    def _ensure_engine(self) -> None:
        if self._engine is not None:
            return
        from cortex.core.paths import CORTEX_DB as DEFAULT_DB_PATH
        from cortex.engine.core.cortex_engine import CortexEngine

        db_val = str(self._db_path) if self._db_path else DEFAULT_DB_PATH
        self._engine = CortexEngine(db_val)
