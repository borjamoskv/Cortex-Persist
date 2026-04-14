"""
CORTEX v7 — Topology WebSocket Router.
Streaming real-time graph updates and Doubt Circuit alerts to the dashboard.
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from cortex.auth.websocket import require_websocket_auth
from cortex.engine.metacognition import DoubtCircuit

router = APIRouter(tags=["topology"])
logger = logging.getLogger("cortex.api.topology")


class TopologyManager:
    """Manages active WebSocket connections for the memory topology dashboard."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._tenant_connections: dict[str, list[WebSocket]] = {}
        self.doubt_circuit = DoubtCircuit()

    async def connect(self, websocket: WebSocket, tenant_id: str):
        """Accepts a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self._tenant_connections.setdefault(tenant_id, []).append(websocket)
        logger.info("Dashboard connected. Active sessions: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Removes a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        empty_tenants: list[str] = []
        for tenant_id, tenant_connections in self._tenant_connections.items():
            if websocket in tenant_connections:
                tenant_connections.remove(websocket)
            if not tenant_connections:
                empty_tenants.append(tenant_id)
        for tenant_id in empty_tenants:
            self._tenant_connections.pop(tenant_id, None)
        logger.info("Dashboard disconnected. Active sessions: %d", len(self.active_connections))

    async def broadcast_event(self, event_type: str, data: dict, *, tenant_id: str):
        """Broadcast a JSON-serialized event only to dashboards in the same tenant."""
        tenant_connections = self._tenant_connections.get(tenant_id, [])
        if not tenant_connections:
            return

        message = json.dumps({"type": event_type, "data": data})
        for connection in list(tenant_connections):
            try:
                await connection.send_text(message)
            except Exception as e:  # noqa: BLE001 — websocket send boundary
                logger.error("Failed to send to websocket: %s", e)
                self.disconnect(connection)

    async def notify_new_memory(self, node_data: dict, neighbors: list[dict] = None):  # type: ignore[type-error]
        """
        Entry point for the consolidation engine to notify the dashboard.
        Evaluates the node through the Doubt Circuit before broadcast.
        """
        tenant_id = str(node_data.get("tenant_id") or "").strip()
        if not tenant_id:
            logger.warning("Skipping topology broadcast without tenant_id: %s", node_data)
            return

        # Neighbors would typically be nodes from the graph store
        alerts = self.doubt_circuit.evaluate_node(node_data, neighbors or [])

        # Broadcast the node
        await self.broadcast_event("NEW_NODE", node_data, tenant_id=tenant_id)

        # Broadcast any alerts found by the Doubt Circuit
        for alert in alerts:
            await self.broadcast_event("DOUBT_ALERT", alert.model_dump(), tenant_id=tenant_id)
            logger.warning("Doubt Circuit Alert: %s on %s", alert.type, alert.node_id)


topology_manager = TopologyManager()


@router.websocket("/ws/v1/topology")
async def websocket_topology_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time memory topology visualization.
    Path: /ws/v1/topology
    """
    auth = await require_websocket_auth(websocket, required_permission="read")
    if auth is None:
        return
    await topology_manager.connect(websocket, auth.tenant_id)
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
