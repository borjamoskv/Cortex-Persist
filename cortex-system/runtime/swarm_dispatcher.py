"""
C5-REAL: Swarm Dispatcher & Collision Scheduler
Author: Borja Moskv / borjamoskv
"""

import asyncio
import random
import logging
from typing import Dict, Any, List
from policies.delegation_map import DelegationMap
from runtime.event_bus import EventBus

logger = logging.getLogger("cortex.system.swarm_dispatcher")

"""
C5-REAL: Swarm Dispatcher & Collision Scheduler
Author: Borja Moskv / borjamoskv
"""

import sys
import os
import json
import uuid
import time
import subprocess
import random
import logging
from typing import Dict, Any, List
from pathlib import Path
from policies.delegation_map import DelegationMap
from runtime.event_bus import EventBus

logger = logging.getLogger("cortex.system.swarm_dispatcher")

class SwarmDispatcher:
    def __init__(self, event_bus: EventBus, engine_instance):
        self.event_bus = event_bus
        self.engine = engine_instance
        self.base_dir = Path(__file__).resolve().parent.parent
        self.swarm_dir = self.base_dir.parent / "moskv-swarm"
        self.inbox_dir = self.swarm_dir / "inbox"
        self.feedback_dir = self.swarm_dir / "feedback"
        self.cortex_feedback_dir = self.base_dir / "runtime" / "swarm_feedback"

        # Ensure directories exist
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        self.cortex_feedback_dir.mkdir(parents=True, exist_ok=True)

    async def schedule_collision(self, session_id: int, prompt: str) -> Dict[str, Any]:
        """
        Coordinates the collision flow by writing a SwarmJob to the moskv-swarm inbox
        and waiting for the feedback JSON payload.
        """
        job_id = uuid.uuid4().hex[:12]
        logger.info(f"Scheduling swarm collision for session={session_id} with job_id={job_id}")

        # 1. Create SwarmJob Payload
        job_data = {
            "job_id": job_id,
            "action": "creative_run",
            "agent_chain": [
                "AgentA.generator",
                "AgentB.adversarial_critic",
                "AgentC.assembler",
                "AgentD.distributor"
            ],
            "constraints": {
                "output_bias": "novelty_over_polish" if random.random() > 0.5 else "polish_over_novelty",
                "require_adversarial_pass": True,
                "allow_contradiction": False,
                "core_vector": "ARTE_PURO",
                "prompt": prompt
            }
        }

        # 2. Write to inbox
        job_path = self.inbox_dir / f"job_{job_id}.json"
        with job_path.open("w", encoding="utf-8") as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Wrote job file: {job_path}")

        # Publish initial events
        await self.event_bus.publish("think", {
            "source": "control_plane",
            "action": "think",
            "status": "dispatched",
            "job_id": job_id
        })

        # 3. Wait for feedback file, fallback to programmatic execution if not found within 1.5 seconds
        feedback_path = self.cortex_feedback_dir / f"feedback_{job_id}.json"
        alt_feedback_path = self.feedback_dir / f"feedback_{job_id}.json"
        
        fb_data = None
        for i in range(15):
            if feedback_path.exists():
                fb_data = json.loads(feedback_path.read_text(encoding="utf-8"))
                break
            if alt_feedback_path.exists():
                fb_data = json.loads(alt_feedback_path.read_text(encoding="utf-8"))
                break
            await asyncio.sleep(0.1)

        if not fb_data:
            logger.info("Feedback not found in active daemon directories. Running swarm_worker synchronously to process queue.")
            worker_script = self.swarm_dir / "swarm_worker.py"
            try:
                subprocess.run(
                    [sys.executable, str(worker_script)],
                    check=True,
                    capture_output=True,
                    cwd=str(self.swarm_dir)
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to run swarm_worker: {e.stderr.decode()}")
                raise RuntimeError(f"Swarm worker execution failed: {e}")

            # Recheck feedback file
            if feedback_path.exists():
                fb_data = json.loads(feedback_path.read_text(encoding="utf-8"))
            elif alt_feedback_path.exists():
                fb_data = json.loads(alt_feedback_path.read_text(encoding="utf-8"))
            else:
                raise TimeoutError(f"Feedback for job {job_id} was not produced by swarm worker.")

        logger.info(f"Swarm worker feedback loaded: {fb_data}")
        metrics = fb_data["estimated_metrics"]

        # Insert metadata and map to database
        assembled_key = f"art_{session_id}_{job_id}"
        cursor = self.engine.conn.cursor()
        
        # 1. Insert Artifact
        cursor.execute("""
            INSERT INTO cortex_artifacts (
                session_id, artifact_key, artifact_type, content, status,
                originality_raw, friction_ms, attention_yield, aesthetic_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, assembled_key, "narrative", f"Payload: creative_run {job_id}", fb_data["artifact_status"],
            metrics["originality_ratio"], 1500, metrics["distribution_yield"], f"hash_{job_id}"
        ))
        
        artifact_id = cursor.lastrowid
        
        # 2. Insert Embedding Mapping
        embedding_key = f"emb_{assembled_key}"
        cursor.execute("""
            INSERT INTO cortex_embedding_map (
                artifact_id, embedding_key, model_name, dims
            ) VALUES (?, ?, ?, ?)
        """, (artifact_id, embedding_key, "default-1536", 1536))
        
        # 3. Write to sqlite-vec vec0 Virtual Table
        vector_1536 = [random.uniform(-0.1, 0.1) for _ in range(1536)]
        binary_emb = self.engine.serialize_embedding(vector_1536)
        cursor.execute("""
            INSERT INTO cortex_embeddings (rowid, embedding)
            VALUES (?, ?)
        """, (artifact_id, binary_emb))
        
        self.engine.conn.commit()

        # Emit validation pass/fail events
        await self.event_bus.publish("feedback", {
            "source": "assembler_prime",
            "action": "feedback",
            "job_id": job_id,
            "status": fb_data["artifact_status"]
        })
        await self.event_bus.publish("commit", {
            "source": "distributor_delta",
            "action": "commit",
            "artifact_id": artifact_id,
            "key": assembled_key
        })

        # Map to returned output format expected by control_plane
        return {
            "status": "committed" if fb_data["artifact_status"] != "rejected" else "collapsed",
            "artifact_id": artifact_id,
            "artifact_key": assembled_key,
            "metrics": {
                "originality_raw": metrics["originality_ratio"],
                "friction_ms": 1500,
                "attention_yield": metrics["distribution_yield"]
            }
        }
