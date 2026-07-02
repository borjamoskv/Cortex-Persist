import json
import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from babylon60.agents.primitives.dispatcher import apex_dispatcher
from babylon60.engine.entropy import entropy_annihilator

logger = logging.getLogger(__name__)


class SovereignFactSchema(BaseModel):
    """[C5-REAL] Strict Pydantic Schema for storing facts.
    Mandatorily exiges 'provenance' and 'confidence_score' to prevent C4-SIM leakage.
    """

    project: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    provenance: str = Field(..., min_length=1)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    fact_type: str = Field(default="knowledge")
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AutoCrystallizer:
    """
    C5-REAL Kinetic Engine: AutoCrystallizer
    Converts raw, stochastic interactions (transcripts/prompts) into
    immutable, structurally sound artifacts (Facts/Nodes) and freezes them.
    """

    def __init__(self) -> None:
        pass

    def validate_facts_json(self, raw_json: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        [C5-REAL] Validates a list of facts (e.g. from _facts.json) using SovereignFactSchema.
        Raises pydantic.ValidationError if validation fails.
        """
        if isinstance(raw_json, str):
            try:
                data = json.loads(raw_json)
            except (json.JSONDecodeError, TypeError) as e:
                raise ValueError(f"Invalid JSON format: {e}") from e
        else:
            data = raw_json

        if not isinstance(data, list):
            raise ValueError("Input data must be a list of facts.")

        validated_facts = []
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"Fact at index {idx} must be a JSON object/dictionary.")
            try:
                validated_fact = SovereignFactSchema(**item)
                validated_facts.append(validated_fact.model_dump())
            except ValidationError as e:
                logger.error(f"[AutoCrystallizer] Ingestion Validation failed at index {idx}: {e}")
                raise

        return validated_facts

    def crystallize_fact(self, raw_data: str) -> dict[str, Any]:
        """
        1. Purges Anergy.
        2. Applies Thermodynamic Compression (Ω4).
        3. Freezes memory structure.
        """
        logger.info("[AutoCrystallizer] Initiating state collapse.")

        # Step 1: Purge conversational slop
        purged_data = entropy_annihilator.purge_slop(raw_data)

        # Step 2: Thermodynamic compression
        compressed_data = entropy_annihilator.thermodynamically_compress(purged_data)

        # Step 3: Structural formulation
        fact_dict = {
            "content": compressed_data,
            "entropy_score": apex_dispatcher.execute("OP_MEASURE_SHANNON", data=compressed_data),
            "crystallized": True,
        }

        # Step 4: OP_FREEZE_MEM
        frozen_fact = apex_dispatcher.execute("OP_FREEZE_MEM", state=fact_dict)

        logger.info(
            f"[AutoCrystallizer] Fact crystallized. Entropy: {fact_dict['entropy_score']:.2f}"
        )
        return frozen_fact


auto_crystallizer = AutoCrystallizer()
