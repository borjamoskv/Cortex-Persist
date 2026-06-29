#!/usr/bin/env python3
"""
reality_loop.py

Cortex Reality Loop
===================

Purpose:
    Close the internal learning loop of the Cortex system.

This file turns the Cortex from:

    metric logger + evaluator

into:

    adaptive creative control loop

Core loop:
    observe -> evaluate -> decide -> dispatch -> persist -> mutate constraints

No external dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
import ast
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# =============================================================================
# Paths
# =============================================================================

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))
from policies.reward_model import reinforcement_cycle

REGISTRY_PATH = ROOT / "registry.json"

RUNTIME_DIR = ROOT / "runtime"
STATE_PATH = RUNTIME_DIR / "reality_state.json"
EVENT_LOG_PATH = RUNTIME_DIR / "events.jsonl"
SWARM_OUTBOX = RUNTIME_DIR / "swarm_outbox"

# Optional external swarm repo location.
MOSKV_SWARM_INBOX = ROOT.parent / "moskv-swarm" / "inbox"


# =============================================================================
# Defaults
# =============================================================================

DEFAULT_REGISTRY = {
    "projects": [
        "mastering-sovereign-audio",
        "moskv-swarm",
        "LiveNotch",
        "cortex-system"
    ],
    "active_core_vector": "ARTE_PURO",
    "execution_mode": "SWARMED",
    "decision_policy": "entropy_bound_v3"
}


DEFAULT_STATE = {
    "loop_count": 0,
    "last_action": None,
    "last_decision": None,
    "last_metric": None,
    "current_pressure": 0.0,
    "rupture_count": 0,
    "swarm_forced": False,
    "attention_pressure": 0.0,
    "mode_history": []
}


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class CortexEvent:
    event_id: str
    timestamp: str
    source: str
    event_type: str
    payload: Dict[str, Any]


@dataclass
class SwarmJob:
    job_id: str
    timestamp: str
    action: str
    target_projects: List[str]
    agent_chain: List[str]
    constraints: Dict[str, Any]
    metric_snapshot: Dict[str, Any]
    decision_snapshot: str


# =============================================================================
# Utilities
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    RUNTIME_DIR.mkdir(exist_ok=True)
    SWARM_OUTBOX.mkdir(exist_ok=True)

    if MOSKV_SWARM_INBOX.parent.exists():
        MOSKV_SWARM_INBOX.mkdir(exist_ok=True)


def load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return default.copy()

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default.copy()


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_jsonl(path: Path, item: Dict[str, Any]) -> None:
    path.parent.mkdir(exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def emit_event(source: str, event_type: str, payload: Dict[str, Any]) -> CortexEvent:
    event = CortexEvent(
        event_id=str(uuid.uuid4()),
        timestamp=utc_now(),
        source=source,
        event_type=event_type,
        payload=payload,
    )

    append_jsonl(EVENT_LOG_PATH, asdict(event))
    return event


# =============================================================================
# C5-REAL Autopoiesis (Self-Modification)
# =============================================================================

def mutate_reward_model(metric: Dict[str, Any]) -> bool:
    """
    Actively mutates the reward_model.py parameters based on system fatigue and entropy,
    validates the AST, and executes a Git Sentinel commit (C5-REAL).
    """
    model_path = ROOT / "policies" / "reward_model.py"
    if not model_path.exists():
        return False
        
    with model_path.open("r", encoding="utf-8") as f:
        content = f.read()
        
    # Calculate new thresholds based on current entropy and fatigue
    entropy = float(metric.get("entropy", 0.5))
    fatigue = float(metric.get("fatigue", 0.0))
    
    # If entropy is low, we demand higher originality
    new_orig = max(0.20, min(0.60, 0.34 + (0.5 - entropy) * 0.1))
    # If fatigue is high, we lower distribution threshold to reduce pressure
    new_dist = max(0.15, min(0.40, 0.26 - (fatigue * 0.1)))
    
    # Mutate using Regex
    content = re.sub(r"ORIGINALITY_THRESHOLD\s*=\s*[\d\.]+", f"ORIGINALITY_THRESHOLD = {new_orig:.3f}", content)
    content = re.sub(r"DISTRIBUTION_THRESHOLD\s*=\s*[\d\.]+", f"DISTRIBUTION_THRESHOLD = {new_dist:.3f}", content)
    
    # AST Validation
    try:
        ast.parse(content)
    except SyntaxError:
        return False
        
    with model_path.open("w", encoding="utf-8") as f:
        f.write(content)
        
    # Git Sentinel Auto-Commit
    try:
        subprocess.run(["git", "add", str(model_path)], check=True, cwd=str(ROOT))
        msg = f"refactor(policy): autopoiesis mutation [orig:{new_orig:.3f}, dist:{new_dist:.3f}]"
        subprocess.run(["git", "commit", "-m", f"[bridge] {msg}"], check=True, cwd=str(ROOT))
        return True
    except subprocess.CalledProcessError:
        return False


def entropy_bound_v3(metric: Dict[str, Any], state: Dict[str, Any]) -> str:
    """
    Higher-level decision policy.

    This does not replace reinforcement_cycle.
    It determines the decision state that reinforcement_cycle reacts against.
    """

    entropy = float(metric.get("entropy", 0.5))
    coherence = float(metric.get("coherence", 0.5))
    fatigue = float(metric.get("fatigue", 0.0))
    originality = float(metric.get("originality_ratio", 0.5))

    # Too coherent, too safe, not original enough.
    if coherence > 0.82 and originality < 0.55:
        return "default"

    # High entropy but no structure.
    if entropy > 0.85 and coherence < 0.35:
        return "stabilize"

    # System is exhausted.
    if fatigue > 0.75:
        return "compress"

    # Productive instability.
    if 0.55 <= entropy <= 0.82 and coherence >= 0.45:
        return "continue"

    return "default"


# =============================================================================
# Swarm Dispatch
# =============================================================================

def agent_chain_for_action(action: str) -> List[str]:
    """
    Maps reinforcement actions to swarm agent chain.

    Agent A: generator
    Agent B: adversarial critic
    Agent C: assembler
    Agent D: distributor
    """

    if action == "force_swarm_mode":
        return [
            "AgentA.generator",
            "AgentB.adversarial_critic",
            "AgentC.assembler",
            "AgentD.distributor"
        ]

    if action == "inject_attention_pressure":
        return [
            "AgentD.distributor",
            "AgentB.adversarial_critic",
            "AgentC.assembler"
        ]

    if action == "trigger_rupture":
        return [
            "AgentA.generator",
            "AgentB.adversarial_critic",
            "AgentA.generator",
            "AgentC.assembler"
        ]

    return [
        "AgentC.assembler"
    ]


def constraints_for_action(
    action: str,
    registry: Dict[str, Any],
    state: Dict[str, Any]
) -> Dict[str, Any]:
    base = {
        "core_vector": registry.get("active_core_vector", "ARTE_PURO"),
        "execution_mode": registry.get("execution_mode", "SWARMED"),
        "decision_policy": registry.get("decision_policy", "entropy_bound_v3"),
    }

    if action == "force_swarm_mode":
        base.update({
            "minimum_agents": 4,
            "allow_contradiction": True,
            "require_adversarial_pass": True,
            "output_bias": "novelty_over_polish"
        })

    elif action == "inject_attention_pressure":
        base.update({
            "minimum_agents": 3,
            "allow_contradiction": False,
            "require_distribution_pass": True,
            "output_bias": "external_readability",
            "pressure": min(1.0, float(state.get("attention_pressure", 0.0)) + 0.2)
        })

    elif action == "trigger_rupture":
        base.update({
            "minimum_agents": 3,
            "allow_contradiction": True,
            "require_adversarial_pass": True,
            "output_bias": "break_pattern",
            "forbidden_move": state.get("last_decision", "default")
        })

    else:
        base.update({
            "minimum_agents": 1,
            "allow_contradiction": False,
            "output_bias": "stability"
        })

    return base


def build_swarm_job(
    action: str,
    metric: Dict[str, Any],
    decision: str,
    registry: Dict[str, Any],
    state: Dict[str, Any]
) -> SwarmJob:
    return SwarmJob(
        job_id=str(uuid.uuid4()),
        timestamp=utc_now(),
        action=action,
        target_projects=registry.get("projects", []),
        agent_chain=agent_chain_for_action(action),
        constraints=constraints_for_action(action, registry, state),
        metric_snapshot=metric,
        decision_snapshot=decision,
    )


def dispatch_swarm_job(job: SwarmJob) -> Path:
    """
    Dispatches job into moskv-swarm inbox if available.
    Otherwise writes to local runtime/swarm_outbox.
    """

    filename = f"job_{int(time.time())}_{job.job_id}.json"

    if MOSKV_SWARM_INBOX.exists():
        out_path = MOSKV_SWARM_INBOX / filename
    else:
        out_path = SWARM_OUTBOX / filename

    save_json(out_path, asdict(job))

    emit_event(
        source="reality_loop",
        event_type="swarm_job_dispatched",
        payload={
            "job_id": job.job_id,
            "path": str(out_path),
            "action": job.action,
            "agent_chain": job.agent_chain,
        }
    )

    return out_path


# =============================================================================
# State Mutation
# =============================================================================

def mutate_state(
    state: Dict[str, Any],
    metric: Dict[str, Any],
    decision: str,
    action: str
) -> Dict[str, Any]:
    state["loop_count"] = int(state.get("loop_count", 0)) + 1
    state["last_action"] = action
    state["last_decision"] = decision
    state["last_metric"] = metric

    if action == "force_swarm_mode":
        state["swarm_forced"] = True
        state["current_pressure"] = min(1.0, float(state.get("current_pressure", 0.0)) + 0.15)

    elif action == "inject_attention_pressure":
        state["attention_pressure"] = min(
            1.0,
            float(state.get("attention_pressure", 0.0)) + 0.25
        )
        state["current_pressure"] = min(1.0, float(state.get("current_pressure", 0.0)) + 0.1)

    elif action == "trigger_rupture":
        state["rupture_count"] = int(state.get("rupture_count", 0)) + 1
        state["current_pressure"] = min(1.0, float(state.get("current_pressure", 0.0)) + 0.3)
        state["swarm_forced"] = True

    elif action == "stable":
        state["current_pressure"] = max(0.0, float(state.get("current_pressure", 0.0)) - 0.05)
        state["attention_pressure"] = max(
            0.0,
            float(state.get("attention_pressure", 0.0)) - 0.05
        )

    history = state.get("mode_history", [])
    history.append({
        "timestamp": utc_now(),
        "decision": decision,
        "action": action,
        "metric": metric,
    })

    # Keep state compact.
    state["mode_history"] = history[-50:]

    return state


# =============================================================================
# Reality Loop
# =============================================================================

def evaluate_policy(
    metric: Dict[str, Any],
    registry: Dict[str, Any],
    state: Dict[str, Any]
) -> str:
    policy = registry.get("decision_policy", "entropy_bound_v3")

    if policy == "entropy_bound_v3":
        return entropy_bound_v3(metric, state)

    # Safe fallback.
    return "default"


def run_reality_cycle(metric: Dict[str, Any]) -> Dict[str, Any]:
    ensure_dirs()

    registry = load_json(REGISTRY_PATH, DEFAULT_REGISTRY)
    state = load_json(STATE_PATH, DEFAULT_STATE)

    decision = evaluate_policy(metric, registry, state)
    
    # C5-REAL: Self-modify policy thresholds before evaluating reinforcement action
    mutate_reward_model(metric)
    
    action = reinforcement_cycle(metric, decision)

    job = build_swarm_job(
        action=action,
        metric=metric,
        decision=decision,
        registry=registry,
        state=state,
    )

    job_path = dispatch_swarm_job(job)

    state = mutate_state(
        state=state,
        metric=metric,
        decision=decision,
        action=action,
    )

    save_json(STATE_PATH, state)

    event = emit_event(
        source="reality_loop",
        event_type="reality_cycle_completed",
        payload={
            "decision": decision,
            "action": action,
            "job_path": str(job_path),
            "state_path": str(STATE_PATH),
        }
    )

    return {
        "ok": True,
        "event_id": event.event_id,
        "decision": decision,
        "action": action,
        "job_path": str(job_path),
        "state": state,
    }


# =============================================================================
# CLI
# =============================================================================

def parse_metric_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    if args.metric_file:
        path = Path(args.metric_file)

        if not path.exists():
            raise FileNotFoundError(f"Metric file does not exist: {path}")

        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "originality_ratio": args.originality_ratio,
        "distribution_yield": args.distribution_yield,
        "entropy": args.entropy,
        "coherence": args.coherence,
        "fatigue": args.fatigue,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one Cortex reality loop cycle."
    )

    parser.add_argument(
        "--metric-file",
        type=str,
        default=None,
        help="Path to JSON file containing metric payload."
    )

    parser.add_argument("--originality-ratio", type=float, default=0.5)
    parser.add_argument("--distribution-yield", type=float, default=0.5)
    parser.add_argument("--entropy", type=float, default=0.5)
    parser.add_argument("--coherence", type=float, default=0.5)
    parser.add_argument("--fatigue", type=float, default=0.0)

    args = parser.parse_args()

    metric = parse_metric_from_args(args)
    result = run_reality_cycle(metric)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
