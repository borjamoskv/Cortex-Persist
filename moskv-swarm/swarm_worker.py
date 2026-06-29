#!/usr/bin/env python3
"""
swarm_worker.py

Cortex Swarm Worker
===================

Purpose:
    Consume SwarmJob payloads from inbox, execute agent chain,
    produce artifact, emit feedback metrics.

This closes the loop:
    Cortex decides -> Swarm executes -> Swarm reports -> Cortex adapts
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# =============================================================================
# Paths
# =============================================================================

ROOT = Path(__file__).resolve().parent

INBOX = ROOT / "inbox"
PROCESSING = ROOT / "processing"
OUTBOX = ROOT / "outbox"
FEEDBACK = ROOT / "feedback"

# Fallback to cortex-system runtime feedback if sibling repo exists.
CORTEX_FEEDBACK = ROOT.parent / "cortex-system" / "runtime" / "swarm_feedback"


# =============================================================================
# Utilities
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    for d in (INBOX, PROCESSING, OUTBOX, FEEDBACK, CORTEX_FEEDBACK):
        d.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =============================================================================
# Agent Base
# =============================================================================

class Agent:
    name: str = "base"

    def run(self, artifact: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class GeneratorAgent(Agent):
    name = "AgentA.generator"

    def run(self, artifact: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        bias = context.get("output_bias", "novelty_over_polish")
        prompt = context.get("prompt", "Generate an oblique artistic concept.")
        
        # System instructions to shape output format
        model_prompt = (
            f"You are a C5-REAL swarm creative generator. "
            f"Process input: '{prompt}' with bias: '{bias}'. "
            f"Output only the raw aesthetic concept description, compressed, dense. No preambles, no apologies."
        )

        ollama_url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3",
            "prompt": model_prompt,
            "stream": False,
            "options": {
                "temperature": 0.85
            }
        }
        
        content = None
        entropy_score = 0.5
        
        import urllib.request
        import urllib.error

        try:
            # Check available models first
            req_tags = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req_tags, timeout=1.0) as response:
                tags_data = json.loads(response.read().decode("utf-8"))
                models = [m["name"] for m in tags_data.get("models", [])]
                if models:
                    payload["model"] = models[0]
                    
            # Make the actual generation request
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                ollama_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5.0) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content = res_data.get("response", "").strip()
                
            if content:
                words = content.lower().split()
                unique_words = set(words)
                if words:
                    entropy_score = min(0.95, max(0.10, len(unique_words) / len(words)))
                    
        except Exception as e:
            # Fallback silently to stub
            pass
            
        if not content:
            content = f"raw_output_{bias}_{uuid.uuid4().hex[:6]}"
            entropy_score = 0.7 if "rupture" in bias or "novelty" in bias else 0.5

        raw = {
            "seed": uuid.uuid4().hex[:8],
            "bias": bias,
            "form": "unstructured",
            "content": content,
            "entropy_target": round(entropy_score, 3),
        }

        artifact["generator"] = raw
        artifact["status"] = "generated"
        return artifact


class CriticAgent(Agent):
    name = "AgentB.adversarial_critic"

    def run(self, artifact: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        require_pass = context.get("require_adversarial_pass", False)
        allow_contradiction = context.get("allow_contradiction", False)

        raw = artifact.get("generator", {})
        entropy = raw.get("entropy_target", 0.5)

        # Simple adversarial rule: high entropy without coherence is rejected.
        score = entropy * 0.6 + (0.3 if allow_contradiction else 0.1)

        verdict = {
            "score": round(score, 3),
            "passed": score > 0.45,
            "require_pass": require_pass,
            "notes": "entropy_acceptable" if score > 0.45 else "too_chaotic",
        }

        artifact["critic"] = verdict

        if require_pass and not verdict["passed"]:
            artifact["status"] = "rejected"
            artifact["rejection_reason"] = "adversarial_fail"
        else:
            artifact["status"] = "approved"

        return artifact


class AssemblerAgent(Agent):
    name = "AgentC.assembler"

    def run(self, artifact: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if artifact.get("status") == "rejected":
            return artifact

        raw = artifact.get("generator", {})
        assembled = {
            "version": "v1",
            "content": raw.get("content", ""),
            "form": "structured",
            "timestamp": utc_now(),
            "core_vector": context.get("core_vector", "ARTE_PURO"),
        }

        artifact["assembled"] = assembled
        artifact["status"] = "assembled"
        return artifact


class DistributorAgent(Agent):
    name = "AgentD.distributor"

    def run(self, artifact: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if artifact.get("status") == "rejected":
            return artifact

        assembled = artifact.get("assembled", {})
        final = {
            "artifact_id": uuid.uuid4().hex,
            "format": "cortex_output",
            "payload": assembled,
            "final_yield": 0.85,
            "distribution_ready": True,
        }

        artifact["distributed"] = final
        artifact["status"] = "distributed"
        return artifact


AGENT_REGISTRY: Dict[str, Agent] = {
    "AgentA.generator": GeneratorAgent(),
    "AgentB.adversarial_critic": CriticAgent(),
    "AgentC.assembler": AssemblerAgent(),
    "AgentD.distributor": DistributorAgent(),
}


# =============================================================================
# Feedback Generator
# =============================================================================

def build_feedback(job: Dict[str, Any], artifact: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce metrics that reality_loop.py can consume in its next cycle.
    """

    critic = artifact.get("critic", {})
    generator = artifact.get("generator", {})

    # Estimate metrics from execution result.
    originality = generator.get("entropy_target", 0.5)
    distribution = 1.0 if artifact.get("status") == "distributed" else 0.0
    coherence = critic.get("score", 0.5)
    fatigue = 0.0  # Placeholder: could track queue depth or error rate.

    # Penalize rejected work.
    if artifact.get("status") == "rejected":
        originality *= 0.6
        distribution = 0.0

    return {
        "feedback_id": uuid.uuid4().hex,
        "timestamp": utc_now(),
        "job_id": job.get("job_id"),
        "action": job.get("action"),
        "estimated_metrics": {
            "originality_ratio": round(originality, 3),
            "distribution_yield": round(distribution, 3),
            "entropy": round(originality, 3),
            "coherence": round(coherence, 3),
            "fatigue": round(fatigue, 3),
        },
        "artifact_status": artifact.get("status"),
        "rejection_reason": artifact.get("rejection_reason"),
    }


# =============================================================================
# Worker Core
# =============================================================================

class SwarmWorker:
    def __init__(self):
        ensure_dirs()

    def resolve_agent(self, name: str) -> Agent:
        if name not in AGENT_REGISTRY:
            raise ValueError(f"Unknown agent: {name}")
        return AGENT_REGISTRY[name]

    def process_file(self, path: Path) -> Optional[Dict[str, Any]]:
        processing_path = PROCESSING / path.name

        # Atomic move to processing.
        shutil.move(str(path), str(processing_path))

        job = load_json(processing_path)
        agent_chain: List[str] = job.get("agent_chain", [])
        constraints: Dict[str, Any] = job.get("constraints", {})

        artifact: Dict[str, Any] = {"status": "init"}

        print(f"[WORKER] Job {job.get('job_id')} | chain: {agent_chain}")

        for agent_name in agent_chain:
            agent = self.resolve_agent(agent_name)
            artifact = agent.run(artifact, constraints)

            print(f"  -> {agent.name}: {artifact['status']}")

            if artifact["status"] == "rejected":
                break

        # Save final artifact.
        out_name = f"artifact_{job.get('job_id')}.json"
        out_path = OUTBOX / out_name
        save_json(out_path, artifact)

        # Emit feedback.
        feedback = build_feedback(job, artifact)
        fb_name = f"feedback_{job.get('job_id')}.json"

        # Write to local feedback.
        save_json(FEEDBACK / fb_name, feedback)

        # Write to cortex feedback if available.
        if CORTEX_FEEDBACK.exists():
            save_json(CORTEX_FEEDBACK / fb_name, feedback)

        # Cleanup processing.
        processing_path.unlink(missing_ok=True)

        print(f"[WORKER] Completed. Output: {out_path}")
        return feedback

    def run_once(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        if not INBOX.exists():
            return results

        for path in sorted(INBOX.glob("*.json")):
            try:
                fb = self.process_file(path)
                if fb:
                    results.append(fb)
            except Exception as e:
                print(f"[WORKER ERROR] {path.name}: {e}", file=sys.stderr)

        return results

    def run_daemon(self, interval: float = 5.0) -> None:
        print(f"[WORKER] Daemon started. Watching {INBOX}")
        while True:
            self.run_once()
            time.sleep(interval)


# =============================================================================
# CLI
# =============================================================================

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Cortex Swarm Worker")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=float, default=5.0, help="Poll interval (seconds)")
    args = parser.parse_args()

    worker = SwarmWorker()

    if args.daemon:
        worker.run_daemon(interval=args.interval)
    else:
        results = worker.run_once()
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
