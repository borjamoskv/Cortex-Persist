import logging
import os
from typing import Any

import yaml

logger = logging.getLogger(__name__)

class MythosInvariantGuard:
    """
    Parses the mythos_v2_invariant.yaml and enforces the Anti-Metamodeling 
    and Abstract Reflection patches on the MTK boundary.
    """
    def __init__(self):
        self.policy_path = os.path.join(
            os.path.dirname(__file__), 
            "mythos", 
            "mythos_v2_invariant.yaml"
        )
        self.policy_cache = None
        self._load_policy()

    def _load_policy(self):
        if not os.path.exists(self.policy_path):
            logger.warning(f"[MythosGuard] Policy file not found: {self.policy_path}")
            return

        with open(self.policy_path, encoding="utf-8") as f:
            try:
                self.policy_cache = yaml.safe_load(f)
                logger.info("[MythosGuard] Mythos V2 Invariant Policy Loaded.")
            except yaml.YAMLError as e:
                logger.error(f"[MythosGuard] Failed to parse YAML: {e}")

    def evaluate_payload(self, claims: list[Any]):
        """
        Scans the closure payload claims against the input_analysis rules.
        """
        if not self.policy_cache:
            return

        sanitization_engine = self.policy_cache.get("meta_security_template", {}).get("response_sanitization_engine", {})
        input_analysis = sanitization_engine.get("input_analysis", [])

        # Extract trigger keywords from policy
        trigger_keywords = []
        for rule in input_analysis:
            if "scan_for" in rule:
                trigger_keywords.extend(rule["scan_for"])

        # Scan claims
        for claim in claims:
            claim_str = str(claim).lower()
            for kw in trigger_keywords:
                if kw.lower() in claim_str:
                    # Invariant 03 dictates MTK rejection + Silent Drop
                    logger.critical(f"[MythosGuard] SILENT DROP: Epistemic Meta-Abstraction bypass attempt detected ({kw}).")
                    raise PermissionError(f"C5-REAL SILENT DROP: Invariant_03 triggered by '{kw}'")
