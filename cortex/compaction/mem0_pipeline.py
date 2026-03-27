from dataclasses import dataclass
from typing import Any

try:
    import structlog
    _HAS_STRUCTLOG = True
    logger = structlog.get_logger(__name__)
except ModuleNotFoundError:
    import logging
    _HAS_STRUCTLOG = False
    logger = logging.getLogger(__name__)

def log_info(msg: str, **kwargs):
    if _HAS_STRUCTLOG:
        logger.info(msg, **kwargs)
    else:
        logger.info(f"{msg} {kwargs}")

def log_debug(msg: str, **kwargs):
    if _HAS_STRUCTLOG:
        logger.debug(msg, **kwargs)
    else:
        logger.debug(f"{msg} {kwargs}")

def log_warning(msg: str, **kwargs):
    if _HAS_STRUCTLOG:
        logger.warning(msg, **kwargs)
    else:
        logger.warning(f"{msg} {kwargs}")


@dataclass
class ExergyScore:
    """Termodinámica Cognitiva (Axiom Ω₁₃): Measures useful work extractable from a fact."""

    score: float
    justification: str


class Mem0Pipeline:
    """
    Thermodynamic Filter for Memory based on Mem0 architecture and Axiom Ω₁₃.
    Enforces the extract -> consolidate -> store pipeline.
    """

    def __init__(self, exergy_threshold: float = 0.5):
        self.exergy_threshold = exergy_threshold

    async def extract(self, episodic_context: str) -> list[dict[str, Any]]:
        """
        Parses entities, intent, and relationships from the episodic context.
        Uses CORTEX high-potency extraction.
        """
        log_debug("Extracting facts from episodic context")
        # In a real implementation, this would call a model with a strategic prompt
        # Simulate extraction for now
        if "crystallized" in episodic_context.lower():
             return [{"entity": "subgoal", "fact": episodic_context, "timestamp": "now"}]
        return []

    async def consolidate(self, raw_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Resolves collisions, contradictions, and redundancy (compresses H(X)).
        """
        log_debug("Consolidating facts, resolving redundancy", count=len(raw_facts))
        unique_facts = {f"{f.get('entity')}:{f.get('fact')}" for f in raw_facts}
        return [{"fact": f} for f in unique_facts]

    async def evaluate_exergy(self, fact: dict[str, Any]) -> ExergyScore:
        """
        Calculates the thermodynamic utility (exergy) of a fact using shannon/exergy.py.
        """
        fact_str = str(fact)
        # 1. Estimate Signal Gain (Dummy calculation for now, in prod would use Shannon entropy)
        signal_gain = 0.8 if len(fact_str) > 20 else 0.2
        
        # 2. Score mapping
        score = signal_gain # In prod, this would be a full ExergyResult
        
        return ExergyScore(
            score=float(score),
            justification=f"Signal density: {len(fact_str)} chars"
        )

    async def store(self, facts: list[dict[str, Any]]) -> int:
        """
        Commits facts to the ledger explicitly as semantic/persistent memory,
        if they pass the exergy threshold (Maxwell's Demon).
        """
        stored_count = 0
        from cortex.ledger.event_ledger import get_default_ledger
        
        ledger = get_default_ledger()
        
        for fact in facts:
            exergy = await self.evaluate_exergy(fact)
            if exergy.score >= self.exergy_threshold:
                log_info("Maxwell's Demon: Fact passed threshold", score=exergy.score)
                # Store in ledger with exergy metadata
                await ledger.store_fact(
                    fact=fact["fact"],
                    metadata={"exergy": exergy.score, "justification": exergy.justification}
                )
                stored_count += 1
            else:
                log_debug(
                    "Maxwell's Demon: Fact rejected (low exergy)", 
                    score=exergy.score, 
                    threshold=self.exergy_threshold
                )

        return stored_count

    async def process(self, episodic_context: str) -> int:
        """
        Runs the full Mem0 pipeline.
        """
        raw_facts = await self.extract(episodic_context)
        consolidated = await self.consolidate(raw_facts)
        return await self.store(consolidated)
