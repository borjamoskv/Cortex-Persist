import json
import hashlib
import re
import math
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from db import record_memory_event, query_events_native
except ImportError:
    # Fallback for standalone testing
    def record_memory_event(*args, **kwargs): print(f"[synthetic-DB] Record: {args} {kwargs}")
    def query_events_native(*args, **kwargs): return []

class ExergyGovernor:
    """
    ∴ Ω-Governor: Sovereign Efficiency Controller.
    Law Ω₂: Work Useful / Energy Total.
    """
    
    MODEL_TIERS = {
        "gemini-3.1-pro": {"tier": "HIGH", "exergy_cost": 1.0, "vsa_alignment": 0.99},
        "gemini-3-flash": {"tier": "LOW", "exergy_cost": 0.08, "vsa_alignment": 0.95},
        "claude-3-5-sonnet": {"tier": "HIGH", "exergy_cost": 1.5, "vsa_alignment": 0.98},
        "nemotron-3-nano:4b": {"tier": "LOW", "exergy_cost": 0.07, "vsa_alignment": 0.96},
    }

    ROUTING_THRESHOLDS = {
        "LOW_COMPLEXITY_LIMIT": 0.25, # More conservative
        "HIGH_CONFIDENCE_MIN": 0.85,  # Min confidence to allow downgrade
        "TOKEN_ESTIMATE_FALLBACK": 512
    }

    def __init__(self):
        self.history_limit = 100

    def calculate_pci(self, prompt: str, tools: Optional[List] = None) -> float:
        """
        Calculates the Prompt Complexity Index (PCI).
        Enforces feaciente logic: detecting high-entropy instructions.
        """
        char_count = len(prompt)
        volume_score = math.log10(max(1, char_count / 100)) / 2.0
        
        structure_score = 0
        if "```" in prompt: structure_score += 0.25 # Implicit logic blocks
        if re.search(r"(verify|audit|security|exploit|truth)", prompt, re.I):
            structure_score += 0.3 # Critical domain keywords
        if "{" in prompt and "}" in prompt: structure_score += 0.1
        
        tool_score = (len(tools) * 0.2) if tools else 0
        
        pci = volume_score + structure_score + tool_score
        return round(min(pci, 2.0), 3)

    def get_routing_confidence(self, pci: float, prompt_hash: str) -> float:
        """
        Calculates the probability that the routing decision is optimal.
        Uses historical ledger 'hits' to verify consistency.
        """
        events = query_events_native("exergy", 20)
        if not events:
            return 0.5 # Default uncertainty
            
        exact_matches = [e for e in events if e.get("subject_hash") == prompt_hash]
        if exact_matches:
            return 1.0 # Definitivo (Previously encountered)
            
        similar_pci = [e for e in events if abs(json.loads(e.get("metadata_json", "{}")).get("pci", 0) - pci) < 0.05]
        confidence = 0.5 + (len(similar_pci) / 40.0) # Increases with historical density
        
        return min(confidence, 0.95)

    def route(self, prompt: str, requested_model: str, tools: Optional[List] = None) -> Dict[str, Any]:
        """
        ∴ Feaciente Governance: Decides model with explicit confidence score.
        If confidence < threshold, avoids optimization to preserve exergy integrity.
        """
        pci = self.calculate_pci(prompt, tools)
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        confidence = self.get_routing_confidence(pci, prompt_hash)
        
        target_model = requested_model
        status = "OPERATOR_OVERRIDE"
        
        # Rule: Optimization only allowed if PCI is low AND confidence is high
        if pci < self.ROUTING_THRESHOLDS["LOW_COMPLEXITY_LIMIT"]:
            if confidence >= self.ROUTING_THRESHOLDS["HIGH_CONFIDENCE_MIN"]:
                if "pro" in requested_model.lower():
                    # Feaciente downgrade to Flash
                    target_model = "gemini-3-flash"
                    status = "AUTONOMOUS_OPTIMIZATION_VERIFIED"
            else:
                status = "OPTIMIZATION_HELD_BACK_LOW_CONFIDENCE"
        
        return {
            "model": target_model,
            "pci": pci,
            "confidence": round(confidence, 2),
            "status": status,
            "original_request": requested_model
        }

    def log_result(self, prompt: str, routing_info: Dict, actual_tokens: int, duration_ms: float):
        """
        Seals the transaction. Adds 'optimal_choice_verified' if exergy yield > 0.9.
        """
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        exergy_yield = round(routing_info["pci"] / (actual_tokens / 1000.0 + 0.001), 3)
        
        metadata = {
            "pci": routing_info["pci"],
            "model": routing_info["model"],
            "confidence": routing_info["confidence"],
            "actual_tokens": actual_tokens,
            "duration_ms": duration_ms,
            "exergy_yield": exergy_yield,
            "optimal_verified": exergy_yield > 0.85
        }
        
        record_memory_event(
            role="exergy",
            content=f"Ω-Governor Result: {routing_info['status']} | Yield: {exergy_yield}",
            subject_hash=prompt_hash,
            metadata=metadata
        )

if __name__ == "__main__":
    gov = ExergyGovernor()
    test_prompts = [
        "What is 2+2?",
        "Audit this smart contract for reentrancy vulnerabilities in the callback function: ```solidity ... ```"
    ]
    for p in test_prompts:
        print(f"\n[*] testing prompt: '{p[:40]}...'")
        print(json.dumps(gov.route(p, "gemini-3.1-pro"), indent=2))


if __name__ == "__main__":
    gov = ExergyGovernor()
    test_prompt = "Tell me a joke about robots."
    print(f"[*] Testing Ω-Governor with: '{test_prompt}'")
    decision = gov.route(test_prompt, "gemini-1.5-pro")
    print(json.dumps(decision, indent=2))
