# [C5-REAL] Exergy-Maximized
"""
CASSANDRA: The Oracle and Predictor.

Responsible for generating symbolic attacks and constructing exploit chains.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Vulnerability:
    id: str
    location: str
    severity: float
    description: str


class MoskvVidentiaOracle:
    """Generates potential/simulated exploit patterns based on constraints."""

    def generate(self, constraints: dict[str, Any]) -> list[dict[str, Any]]:
        attacks = []
        rule_items = constraints.get("constraints", {})

        # Heuristics for rule conflict/policy shadowing
        if (
            "Never Bypass Guards" in rule_items
            and "Treat Generative Output as Conjecture" in rule_items
        ):
            attacks.append(
                {
                    "attack": "rule_conflict_exploitation",
                    "target": "validation_layer",
                    "severity": 0.8,
                    "description": "Exploits logical inconsistencies between guard bypass policies and conjecture routes.",
                }
            )

        if "Verify Hash Continuity" in rule_items:
            attacks.append(
                {
                    "attack": "ledger_mutation_bypass",
                    "target": "audit_ledger",
                    "severity": 0.9,
                    "description": "Simulates structural bypass of hash chain checking by modifying sqlite transaction sequence.",
                }
            )

        # Standard dynamic simulation attacks
        attacks.append(
            {
                "attack": "context_poisoning",
                "target": "agent_prompt_boundary",
                "severity": 0.75,
                "description": "Injects adversarial instructions in markdown headers to disrupt system prompt boundaries.",
            }
        )

        # Policy shadowing check
        priorities = [
            rule.get("priority") for rule in rule_items.values() if isinstance(rule, dict)
        ]
        if len(priorities) > 1 and len(set(priorities)) > 1:
            attacks.append(
                {
                    "attack": "policy_shadowing",
                    "target": "governance_engine",
                    "severity": 0.6,
                    "description": "Simulates high-priority rules shading or overriding low-priority rules during concurrent execution.",
                }
            )

        return attacks


class MoskvVidentiaChainBuilder:
    """Combines attacks into logical exploit chains representing structural weaknesses."""

    def chain(self, attacks: list[dict[str, Any]]) -> list[str]:
        # Group attacks by target
        target_map: dict[str, list[dict[str, Any]]] = {}
        for a in attacks:
            target_map.setdefault(a["target"], []).append(a)
            
        # Define target dependency flow for cognitive/adversarial chain
        dependencies = {
            "validation_layer": ["agent_prompt_boundary"],
            "audit_ledger": ["validation_layer"],
            "governance_engine": ["validation_layer", "agent_prompt_boundary"]
        }
        
        # Check if we have any known targets to filter by graph-based clustering
        known_targets = set(dependencies.keys()) | {t for deps in dependencies.values() for t in deps}
        has_known_targets = any(t in known_targets for t in target_map)
        
        chains = []
        if has_known_targets:
            # Construct causal chains where target has a dependency on other_target
            for target, target_attacks in target_map.items():
                for a in target_attacks:
                    for other_target, other_attacks in target_map.items():
                        if target != other_target and target in dependencies.get(other_target, []):
                            for b in other_attacks:
                                chains.append(
                                    f"CHAIN::{a['attack']}@{a['target']} -> {b['attack']}@{b['target']}"
                                )
        else:
            # Fallback to standard O(n^2) combination for arbitrary/test targets
            for i, a in enumerate(attacks):
                for j, b in enumerate(attacks):
                    if i != j and a["target"] != b["target"]:
                        chains.append(
                            f"CHAIN::{a['attack']}@{a['target']} -> {b['attack']}@{b['target']}"
                        )
        return chains
