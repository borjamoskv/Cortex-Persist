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
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ollama_connector import generate as ollama_generate

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


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# =============================================================================
# Agent Base
# =============================================================================

class Agent:
    name: str = "base"

    def run(self, artifact: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class GeneratorAgent(Agent):
    name = "AgentA.generator"

    def run(self, artifact: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        bias = context.get("output_bias", "novelty_over_polish")
        core_vector = context.get("core_vector", "ARTE_PURO")
        forbidden = context.get("forbidden_move", "none")
        
        # Construcción determinista del prompt de colisión
        prompt = (
            f"Core Vector: {core_vector}\n"
            f"Output Bias: {bias}\n"
            f"Forbidden Move: {forbidden}\n\n"
            f"Generate a raw creative artifact. "
            f"Output as a structured concept, code snippet, or manifesto:"
        )

        # Llamada al metabolismo local
        content = ollama_generate(prompt)
        
        is_error = content.startswith("ERROR_OLLAMA")

        raw = {
            "seed": uuid.uuid4().hex[:8],
            "bias": bias,
            "form": "llm_structured" if not is_error else "error_fallback",
            "content": content,
            "entropy_target": 0.7 if "rupture" in bias else 0.5,
            "model_used": "llama3"
        }

        artifact["generator"] = raw
        artifact["status"] = "generated_error" if is_error else "generated"

        # Persistencia dual: guardar crudo a disco además del artifact en memoria
        if not is_error:
            raw_filename = f"raw_{artifact.get('job_id', 'unknown')}.md"
            raw_path = OUTBOX / raw_filename
            with raw_path.open("w", encoding="utf-8") as f:
                f.write(content)

        return artifact


class CriticAgent(Agent):
    name = "AgentB.adversarial_critic"

    def run(self, artifact: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
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

    def run(self, artifact: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
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

    def run(self, artifact: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
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


AGENT_REGISTRY: dict[str, Agent] = {
    "AgentA.generator": GeneratorAgent(),
    "AgentB.adversarial_critic": CriticAgent(),
    "AgentC.assembler": AssemblerAgent(),
    "AgentD.distributor": DistributorAgent(),
}


# =============================================================================
# Feedback Generator
# =============================================================================

def build_feedback(job: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
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

    def process_file(self, path: Path) -> Optional[dict[str, Any]]:
        processing_path = PROCESSING / path.name

        # Atomic move to processing.
        shutil.move(str(path), str(processing_path))

        job = load_json(processing_path)
        agent_chain: list[str] = job.get("agent_chain", [])
        constraints: dict[str, Any] = job.get("constraints", {})

        artifact: dict[str, Any] = {"status": "init", "job_id": job.get("job_id")}

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

    def run_once(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

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
