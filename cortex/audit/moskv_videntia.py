# [C5-REAL] Exergy-Maximized
"""
CASSANDRA: The Oracle and Predictor.

Responsible for generating symbolic attacks and constructing exploit chains.
"""

from __future__ import annotations

import json
import subprocess
import urllib.request
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

    def _get_git_diff(self) -> str:
        try:
            diff = subprocess.check_output(
                ["git", "diff", "--staged"], text=True, stderr=subprocess.DEVNULL
            )
            if not diff.strip():
                diff = subprocess.check_output(
                    ["git", "diff", "HEAD"], text=True, stderr=subprocess.DEVNULL
                )
            return diff
        except subprocess.SubprocessError:
            return ""

    def generate(self, constraints: dict[str, Any]) -> list[dict[str, Any]]:
        diff = self._get_git_diff()

        if diff.strip():
            prompt = f"""You are Moskv-Videntia, an Adversarial Audit Oracle.
Analyze this git diff and evaluate it against the system constraints.
Return ONLY a valid JSON array of vulnerabilities. No markdown, no prose.
Each vulnerability MUST be a dictionary with keys: "attack" (string), "target" (string), "severity" (float 0.0-1.0), "description" (string).
If no structural flaws violate the constraints, return an empty array: []

Constraints:
{json.dumps(constraints)}

Git Diff:
{diff[:4000]}
"""
            payload = {
                "model": "qwen2.5-coder:7b",
                "prompt": prompt,
                "stream": False,
                "format": "json",
            }
            try:
                req = urllib.request.Request(
                    "http://localhost:11434/api/generate",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    raw_read = response.read().decode("utf-8")
                    resp_data = json.loads(raw_read)
                    raw_response_text = resp_data.get("response", "[]").strip()

                    if raw_response_text.startswith("```json"):
                        raw_response_text = (
                            raw_response_text.split("```json")[1].split("```")[0].strip()
                        )
                    elif raw_response_text.startswith("```"):
                        raw_response_text = raw_response_text.split("```")[1].strip()

                    attacks = json.loads(raw_response_text)
                    if isinstance(attacks, dict):
                        if not attacks:
                            return []
                        if "vulnerabilities" in attacks:
                            attacks = attacks["vulnerabilities"]
                        elif "attack" in attacks and "severity" in attacks:
                            return [attacks]

                    if isinstance(attacks, list):
                        return attacks
            except Exception as e:
                import sys

                print(f"[MoskvVidentiaOracle] LLM Call Failed: {e}", file=sys.stderr)
                try:
                    print(
                        f"[MoskvVidentiaOracle] Raw text was: {raw_response_text}", file=sys.stderr
                    )
                except Exception:
                    pass
                # Fallback to simulated heuristics

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
                    "severity": 0.3,
                    "description": "Exploits logical inconsistencies between guard bypass policies and conjecture routes.",
                }
            )

        if "Verify Hash Continuity" in rule_items:
            attacks.append(
                {
                    "attack": "ledger_mutation_bypass",
                    "target": "audit_ledger",
                    "severity": 0.2,
                    "description": "Simulates structural bypass of hash chain checking by modifying sqlite transaction sequence.",
                }
            )

        # Standard dynamic simulation attacks
        attacks.append(
            {
                "attack": "context_poisoning",
                "target": "agent_prompt_boundary",
                "severity": 0.15,
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
                    "severity": 0.1,
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
            "governance_engine": ["validation_layer", "agent_prompt_boundary"],
        }

        # Check if we have any known targets to filter by graph-based clustering
        known_targets = set(dependencies.keys()) | {
            t for deps in dependencies.values() for t in deps
        }
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
