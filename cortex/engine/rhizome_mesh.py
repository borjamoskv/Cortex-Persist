import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger("cortex.engine.rhizome_mesh")

class RhizomeMesh:
    """
    [C5-REAL] Rhizome Mesh (Event-Driven Pub/Sub).
    Erradica la jerarquía Parent -> Subagent. Los agentes se comunican de forma
    descentralizada publicando y suscribiéndose a mesetas de contexto (Plateaus).
    """
    def __init__(self):
        # Mapeo de Evento (Plateau) -> Lista de Callbacks (Líneas de fuga)
        self._subscribers: dict[str, list[Callable[[Any], Awaitable[None]]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[Any], Awaitable[None]]):
        """Un nodo se adhiere pasivamente al rizoma esperando un evento específico."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"[RHIZOME] Nodo anclado a la meseta: {event_type}")

    async def publish(self, event_type: str, payload: Any):
        """
        Emite un evento a la malla. La ejecución es concurrente y no jerárquica.
        No hay coordinador esperando o bloqueando el hilo de ejecución primario.
        """
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            logger.debug(f"[RHIZOME] Evento huérfano (sin nodos receptores): {event_type}")
            return
            
        # Expansión Clonal: Ejecutamos todos los handlers concurrentemente
        tasks = [asyncio.create_task(handler(payload)) for handler in handlers]
        
        # Dejamos que operen independientemente (Desterritorialización)
        # Gather asegura que el bus espera que terminen en la prueba, pero en prod 
        # pueden ser fire-and-forget.
        await asyncio.gather(*tasks)

# Instancia global para la malla asíncrona principal
mesh = RhizomeMesh()
