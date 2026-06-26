# [C5-REAL] Exergy-Maximized
"""Exergy-Aware Cost Scheduler.

Resolves model tier selection (IDLE_STATE, CONSTRUCT_STATE, APEX_STATE)
and handles interrupts/degradation policies (APOPTOSIS, NMI, THERMODYNAMIC_BAILOUT)
based on antigravity_routing_policy.yaml.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.engine.uncategorized.cost_scheduler")

DEFAULT_POLICY_PATH = Path(
    "/Users/borjafernandezangulo/.gemini/antigravity/scratch/exergy_engine/antigravity_routing_policy.yaml"
)


class ExergyCostScheduler:
    """Exergy-Aware Cost Scheduler resolving model tier degradation."""

    def __init__(self, policy_path: Path | str | None = None):
        self.policy_path = Path(policy_path or DEFAULT_POLICY_PATH)
        self.policy = {}
        self._load_policy()

    def _load_policy(self) -> None:
        """Loads routing policy from YAML file."""
        import yaml

        if not self.policy_path.exists():
            logger.warning(
                f"[COST-SCHEDULER] Policy path {self.policy_path} not found. Using empty policy."
            )
            self.policy = {}
            return

        try:
            with open(self.policy_path, encoding="utf-8") as f:
                self.policy = yaml.safe_load(f) or {}
            logger.info(f"[COST-SCHEDULER] Loaded policy from {self.policy_path}")
        except Exception as e:
            logger.error(f"[COST-SCHEDULER] Failed to load policy: {e}")
            self.policy = {}

    def evaluate_interrupts(self, intent: str, context: dict[str, Any]) -> dict[str, Any] | None:
        """
        Evaluate non-maskable interrupts and thermodynamic limits.
        Returns target action/state change if triggered, else None.
        """
        # 1. Non-Maskable Interrupt (NMI): USER_INPUT / intent contains 'PIENSA'
        if "PIENSA" in intent:
            logger.info("[COST-SCHEDULER] ⚡ NMI Triggered: forcing APEX_STATE.")
            return {"action": "FORCE_APEX_STATE", "inject_cot": True, "target_state": "APEX_STATE"}

        # 2. Apoptosis Trigger (Dead code runaway or memory collapse)
        dead_code_ratio = float(context.get("dead_code_ratio", 0.0))
        complexity_penalty = float(context.get("complexity_penalty", 0.0))
        if dead_code_ratio > 0.4 and complexity_penalty > 10.0:
            logger.warning("[COST-SCHEDULER] 💀 APOPTOSIS Triggered: memory collapse detected.")
            return {
                "action": "KILL_PROCESS && PURGE_MEMORY",
                "reason": f"dead_code_ratio={dead_code_ratio}, complexity={complexity_penalty}",
            }

        # 3. Thermodynamic Bailout (Loop degradation)
        loop_count = int(context.get("loop_count", 0))
        resolution_status = bool(context.get("resolution_status", True))
        if loop_count > 3 and not resolution_status:
            logger.warning("[COST-SCHEDULER] ❄️ THERMODYNAMIC_BAILOUT Triggered: degrading to IDLE.")
            return {
                "action": "DEGRADE_TO_IDLE && REQUEST_USER_OVERRIDE",
                "target_state": "IDLE_STATE",
            }

        return None

    def determine_state(self, intent: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Resolves the appropriate inference state (model, thinking, epistemology)
        based on intent and system telemetry context.
        """
        # First check if there's any active interrupt
        interrupt = self.evaluate_interrupts(intent, context)
        if interrupt:
            target_state = interrupt.get("target_state")
            if target_state:
                # If target state is specified, return that state's configuration
                state_config = self._get_state_config(target_state)
                state_config["interrupt_action"] = interrupt.get("action")
                return state_config
            else:
                # Otherwise, return interrupt info directly (e.g. Apoptosis)
                return {
                    "state": "INTERRUPT",
                    "action": interrupt.get("action"),
                    "reason": interrupt.get("reason"),
                }

        # Evaluate trigger conditions for APEX_STATE
        if self._eval_apex_triggers(intent, context):
            return self._get_state_config("APEX_STATE")

        # Evaluate trigger conditions for CONSTRUCT_STATE
        if self._eval_construct_triggers(intent, context):
            return self._get_state_config("CONSTRUCT_STATE")

        # Default fallback to IDLE_STATE
        return self._get_state_config("IDLE_STATE")

    def _get_state_config(self, state_name: str) -> dict[str, Any]:
        """Retrieve state configuration from loaded policy with defaults."""
        states = self.policy.get("inference_states", {})
        config = states.get(state_name, {})

        # Hardcoded defaults if yaml loading is empty
        if not config:
            if state_name == "APEX_STATE":
                config = {
                    "model": "3.1 Pro",
                    "thinking": "Deep Think",
                    "epistemology": "C5-REAL",
                    "max_tokens": 2097152,
                }
            elif state_name == "CONSTRUCT_STATE":
                config = {
                    "model": "3.5 Flash",
                    "thinking": "Avanzado",
                    "epistemology": "C5-REAL",
                    "max_tokens": 32768,
                }
            else:  # IDLE_STATE
                config = {
                    "model": "3.1 Flash-Lite",
                    "thinking": "Estándar",
                    "epistemology": "C4-SIM",
                    "max_tokens": 4096,
                }

        return {
            "state": state_name,
            "model": config.get("model"),
            "thinking": config.get("thinking"),
            "epistemology": config.get("epistemology"),
            "max_tokens": config.get("max_tokens"),
            "allowed_mcp": config.get("allowed_mcp", []),
        }

    def _eval_apex_triggers(self, intent: str, context: dict[str, Any]) -> bool:
        """Evaluate APEX_STATE trigger conditions."""
        # Condition 1: system.entropy_spike == True
        if bool(context.get("system_entropy_spike", False)):
            return True

        # Condition 2: intent contains 'PIENSA', 'arquitectura', 'seguridad', 'auditoría'
        apex_words = ["piensa", "arquitectura", "seguridad", "auditoría", "auditoria"]
        if any(w in intent.lower() for w in apex_words):
            return True

        # Condition 3: target.is_destructive == True
        if bool(context.get("target_is_destructive", False)):
            return True

        return False

    def _eval_construct_triggers(self, intent: str, context: dict[str, Any]) -> bool:
        """Evaluate CONSTRUCT_STATE trigger conditions."""
        # Condition 1: intent contains 'crea', 'añade', 'fix'
        construct_words = ["crea", "añade", "fix", "add", "create", "modificar"]
        if any(w in intent.lower() for w in construct_words):
            return True

        # Condition 2: ast.diff_size > 50
        diff_size = int(context.get("ast_diff_size", 0))
        if diff_size > 50:
            return True

        # Condition 3: git.status == 'dirty'
        git_status = context.get("git_status", "clean")
        if git_status == "dirty":
            return True

        return False

    def select_backend(self, domain: str, intent_kind: str) -> BackendConfig:
        """Resolves backend configuration based on intent evaluation."""
        state_config = self.determine_state(intent_kind, {"domain": domain})
        state_name = state_config["state"]

        if state_name == "APEX_STATE":
            backend_name = "AX"
        elif state_name == "CONSTRUCT_STATE":
            backend_name = "CDP"
        else:
            backend_name = "HITL"

        return BackendConfig(name=backend_name, state_config=state_config)


@dataclass
class BackendConfig:
    name: str
    state_config: dict[str, Any]

    def total_cost(self, domain: str) -> float:
        max_tokens = self.state_config.get("max_tokens", 4096)
        # Empirical exergy cost proxy (USD per 1k tokens)
        return float(max_tokens) / 1000.0 * 0.01
