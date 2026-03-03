"""
CORTEX v7 — Topology WebSocket Router.
Streaming real-time graph updates and Doubt Circuit alerts to the dashboard.
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from cortex.engine.metacognition import DoubtCircuit

router = APIRouter(tags=["topology"])
logger = logging.getLogger("cortex.api.topology")


class TopologyManager:
    """Manages active WebSocket connections for the memory topology dashboard."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.doubt_circuit = DoubtCircuit()

    async def connect(self, websocket: WebSocket):
        """Accepts a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Dashboard connected. Active sessions: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Removes a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("Dashboard disconnected. Active sessions: %d", len(self.active_connections))

    async def broadcast_event(self, event_type: str, data: dict):
        """Broadcasts a JSON-serialized event to all connected dashboards."""
        if not self.active_connections:
            return

        message = json.dumps({"type": event_type, "data": data})
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error("Failed to send to websocket: %s", e)

    async def notify_new_memory(self, node_data: dict, neighbors: list[dict] = None):
        """
        Entry point for the consolidation engine to notify the dashboard.
        Evaluates the node through the Doubt Circuit before broadcast.
        """
        # Neighbors would typically be nodes from the graph store
        alerts = self.doubt_circuit.evaluate_node(node_data, neighbors or [])

        # Broadcast the node
        await self.broadcast_event("NEW_NODE", node_data)

        # Broadcast any alerts found by the Doubt Circuit
        for alert in alerts:
            await self.broadcast_event("DOUBT_ALERT", alert.model_dump())
            logger.warning("Doubt Circuit Alert: %s on %s", alert.type, alert.node_id)


topology_manager = TopologyManager()


@router.websocket("/ws/v1/topology")
async def websocket_topology_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time memory topology visualization.
    Path: /ws/v1/topology
    """
    await topology_manager.connect(websocket)
    try:
        while True:
            # Listening for client commands (e.g. manual noise injection)
            data = await websocket.receive_text()
            try:
                command = json.loads(data)
                if command.get("type") == "INJECT_NOISE":
                    logger.info(
                        "Manual noise injection command received for %s", command.get("node_id")
                    )
                    # Implementation would trigger a re-consolidation with perturbation
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        topology_manager.disconnect(websocket)
