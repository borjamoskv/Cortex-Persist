"""
C5-REAL: Control Plane Orchestrator
Author: Borja Moskv / borjamoskv
"""

import asyncio
import json
import logging
import os
import sys

# Ensure internal modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from policies.abort_rules import AbortRules
from policies.reward_model import reinforcement_cycle
from runtime.session_router import SessionRouter
from runtime.swarm_dispatcher import SwarmDispatcher

from babylon60.events.bus import DistributedEventBus

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cortex.system.control_plane")

class ControlPlane:
    def __init__(self, registry_path: str = "registry.json", db_path: str = "artist_cortex.db"):
        self.registry_path = os.path.abspath(os.path.join(os.path.dirname(__file__), registry_path))
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), db_path))
        self.registry = self._load_registry()
        
        self.session_router = SessionRouter(db_path=self.db_path)
        self.event_bus = DistributedEventBus()
        self.dispatcher = SwarmDispatcher(self.event_bus, self.session_router.engine)
        
        # Subscribe a logger listener to active topics
        for topic in ["think", "feedback", "commit"]:
            self.event_bus.subscribe(topic, self._log_event)

    def _load_registry(self) -> dict:
        with open(self.registry_path, encoding="utf-8") as f:
            return json.load(f)

    async def _log_event(self, event_dict) -> None:
        logger.info(f"[EVENT_BUS] {event_dict.get('source', 'unknown')} emitted '{event_dict.get('action', 'unknown')}': {event_dict}")
        # Insert event log to database if session/artifact context is available
        cursor = self.session_router.engine.conn.cursor()
        session_id = event_dict.get("session_id")
        data = event_dict.get("data", {})
        artifact_id = data.get("artifact_id") if isinstance(data, dict) else None
        cursor.execute("""
            INSERT INTO cortex_events (session_id, artifact_id, event_type, payload)
            VALUES (?, ?, ?, ?)
        """, (session_id, artifact_id, event_dict.get("action", "unknown"), json.dumps(event_dict)))
        self.session_router.engine.conn.commit()

    async def execute_cycle(self, prompt: str, operator_id: str = "borjamoskv") -> dict:
        """
        Executes a single creative validation cycle.
        Returns a dict summarizing metrics, state changes, and evolutionary actions.
        """
        core_vector = self.registry.get("active_core_vector", "ARTE_PURO")
        session_id = self.session_router.route_session(
            operator_id=operator_id,
            core_vector=core_vector,
            notes=f"Control Plane executed cycle for prompt: {prompt}"
        )
        
        try:
            # 1. Dispatch Swarm Pipeline
            result = await self.dispatcher.schedule_collision(session_id, prompt)
            if result["status"] == "collapsed":
                raise RuntimeError("Swarm collision collapsed: no proposals survived Critic B audit.")

            # 2. Evaluate Abort Rules
            metrics = result["metrics"]
            # Convert raw metrics for abort evaluation
            eval_metrics = {
                "originality_raw": metrics["originality_raw"],
                "friction_ms": metrics["friction_ms"],
                "attention_yield": metrics["attention_yield"]
            }
            abort_status = AbortRules.evaluate(eval_metrics)
            if abort_status["abort"]:
                logger.error(f"ABORT TRIGGERED: {abort_status['reason']}")
                # Rollback or flag artifact as rejected in DB
                cursor = self.session_router.engine.conn.cursor()
                cursor.execute("""
                    UPDATE cortex_artifacts
                    SET status = 'rejected'
                    WHERE id = ?
                """, (result["artifact_id"],))
                self.session_router.engine.conn.commit()
                raise RuntimeError(f"Saga abort: {abort_status['reason']}")

            # 3. Trigger Reinforcement Cycle
            # Reinforcement Cycle metric maps:
            reinforce_metric = {
                "originality_ratio": metrics["originality_raw"],
                "distribution_yield": metrics["attention_yield"]
            }
            evolutionary_action = reinforcement_cycle(reinforce_metric, "default")
            logger.info(f"Reinforcement cycle result: {evolutionary_action}")

            # 4. Record metric evaluations in DB
            cursor = self.session_router.engine.conn.cursor()
            for name, val in eval_metrics.items():
                cursor.execute("""
                    INSERT INTO cortex_metrics (artifact_id, metric_name, metric_value, verdict)
                    VALUES (?, ?, ?, 'pass')
                """, (result["artifact_id"], name, float(val)))
            self.session_router.engine.conn.commit()

            # End Session
            self.session_router.end_session(session_id)
            
            return {
                "session_id": session_id,
                "artifact_id": result["artifact_id"],
                "artifact_key": result["artifact_key"],
                "evolutionary_action": evolutionary_action,
                "metrics": eval_metrics,
                "status": "success"
            }
            
        except Exception as e:
            logger.exception("Error executing Control Plane cycle")
            self.session_router.end_session(session_id)
            raise e

# Direct CLI execution entry point
if __name__ == "__main__":
    cp = ControlPlane()
    asyncio.run(cp.execute_cycle(prompt="Genesis of distributed sonic waves"))
