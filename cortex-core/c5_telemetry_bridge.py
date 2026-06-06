import asyncio
import json
import logging
import websockets
from ultramap import UltramapSubstrate

logging.basicConfig(level=logging.INFO, format="📡 [C5-REAL-BRIDGE] %(message)s")

class TelemetryBridge:
    def __init__(self, port=8081):
        self.port = port
        self.umap = UltramapSubstrate()
        self.active_connections = set()
        
    async def register(self, websocket):
        self.active_connections.add(websocket)
        logging.info(f"Client connected. Active visualizers: {len(self.active_connections)}")

    async def unregister(self, websocket):
        self.active_connections.remove(websocket)
        logging.info(f"Client disconnected. Active visualizers: {len(self.active_connections)}")

    async def broadcast_loop(self):
        """Streams the topological state of all active agents at ~60fps (16ms resolution)."""
        logging.info(f"Initiating C5-REAL telemetry broadcast on ws://0.0.0.0:{self.port}")
        while True:
            if self.active_connections:
                # O(1) Memory Scan -> Frame Emission
                state_frame = []
                # Scanning top 250 vectors to prevent DOM overload in visualizer, 
                # maintaining C5-REAL thermodynamic bounds.
                for i in range(250):
                    agent_state = self.umap.get_agent_state(i)
                    if agent_state and agent_state['target']:
                        state_frame.append({
                            "id": i,
                            "x": round(agent_state['x'], 3),
                            "y": round(agent_state['y'], 3),
                            "z": round(agent_state['z'], 3),
                            "target": agent_state['target'],
                            "entropy": round(agent_state['entropy'], 3),
                            "queue_depth": round(agent_state.get('queue_depth', 0.0), 3),
                            "error_rate": round(agent_state.get('error_rate', 0.0), 3),
                            "causal_entropy": round(agent_state.get('causal_entropy', 0.0), 3),
                            "cpu_load": round(agent_state.get('cpu_load', 0.0), 3)
                        })
                
                if state_frame:
                    payload = json.dumps({"type": "FRAME", "data": state_frame})
                    websockets.broadcast(self.active_connections, payload)
            
            await asyncio.sleep(0.016)  # ~60 Hz resolution

    async def handler(self, websocket):
        await self.register(websocket)
        try:
            async for _ in websocket:
                # Accept reverse-telemetry or pings
                pass
        finally:
            await self.unregister(websocket)

    async def start(self):
        async with websockets.serve(self.handler, "0.0.0.0", self.port):
            await self.broadcast_loop()

if __name__ == "__main__":
    bridge = TelemetryBridge()
    try:
        asyncio.run(bridge.start())
    except KeyboardInterrupt:
        logging.info("Telemetry Bridge offline.")
