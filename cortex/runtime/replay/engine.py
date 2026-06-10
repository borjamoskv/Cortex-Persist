# [C5-REAL] Exergy-Maximized
from typing import Any, Type

class DivergenceException(Exception):
    """Lanzada cuando el hash del estado actual diverge del histórico esperado."""
    pass

class ReplayEngine:
    """Motor determinista. Reproduce eventos pasados para reconstruir el estado."""
    
    def __init__(self, state_cls: Type[Any]):
        self.state_cls = state_cls

    def run(self, events: list[dict[str, Any]], expected_hashes: dict[int, str] = None) -> list[dict[str, Any]]:
        """
        Ejecuta los eventos secuencialmente sobre el estado.
        Si se provee expected_hashes (mapeo versión -> hash_esperado), 
        valida rigurosamente la coherencia determinista en cada mutación.
        """
        state = self.state_cls.bootstrap()
        snapshots = [state.snapshot()]
        
        if expected_hashes and state.version in expected_hashes:
            if state.hash != expected_hashes[state.version]:
                raise DivergenceException(
                    f"[DIVERGENCE DETECTED] Version {state.version}: "
                    f"Expected {expected_hashes[state.version]}, got {state.hash}"
                )

        for event in events:
            state.apply_event(event)
            snap = state.snapshot()
            snapshots.append(snap)
            
            if expected_hashes and snap["version"] in expected_hashes:
                if snap["state_hash"] != expected_hashes[snap["version"]]:
                    raise DivergenceException(
                        f"[DIVERGENCE DETECTED] Version {snap['version']}: "
                        f"Expected {expected_hashes[snap['version']]}, got {snap['state_hash']}"
                    )
                    
        return snapshots
