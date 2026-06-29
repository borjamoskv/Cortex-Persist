"""
C5-REAL: Asynchronous Event Bus Broker
Author: Borja Moskv / borjamoskv
"""

import asyncio
from typing import Dict, List, Callable, Any, Awaitable
import logging

logger = logging.getLogger("cortex.system.event_bus")

class Event:
    def __init__(self, event_type: str, payload: Dict[str, Any], emitter: str):
        self.event_type = event_type
        self.payload = payload
        self.emitter = emitter
        self.timestamp = asyncio.get_event_loop().time()

    def __repr__(self) -> str:
        return f"<Event type={self.event_type} emitter={self.emitter} timestamp={self.timestamp}>"

class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[Callable[[Event], Awaitable[None]]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[Event], Awaitable[None]]):
        """Subscribes an async callback to a specific event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        logger.info(f"Registered subscriber for event: {event_type}")

    async def publish(self, event_type: str, payload: Dict[str, Any], emitter: str):
        """Asynchronously publishes an event to all subscribers."""
        event = Event(event_type, payload, emitter)
        logger.debug(f"Publishing event: {event}")
        
        callbacks = self._listeners.get(event_type, [])
        # Also notify wildcard subscribers if any
        callbacks.extend(self._listeners.get("*", []))
        
        if not callbacks:
            return

        tasks = []
        for cb in callbacks:
            tasks.append(cb(event))
            
        await asyncio.gather(*tasks, return_exceptions=True)
