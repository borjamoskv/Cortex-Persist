"""Pydantic V2 schemas for L3 (Prediction) and L4 (Experiment).

Provides strict typing and structural validation for higher-order causal entities.
"""

from enum import Enum
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class ExperimentResult(str, Enum):
    PENDING = "PENDING"
    REFUTED = "REFUTED"
    CORROBORATED = "CORROBORATED"


class ExperimentDesign(BaseModel):
    setup_saga: str = Field(min_length=1)
    execution_trigger: str = Field(min_length=1)
    success_criteria: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class PredictionSchemaL3(BaseModel):
    prediction_id: UUID
    model_id: UUID
    falsifiable_condition: str = Field(min_length=1, description="If model is true, this MUST occur.")
    experiment_design: ExperimentDesign
    experiment_result: Optional[ExperimentResult] = None

    model_config = ConfigDict(extra="forbid")


class ExecutionContext(str, Enum):
    SANDBOX_THREAD = "SANDBOX_THREAD"
    ISOLATED_BRANCH = "ISOLATED_BRANCH"
    DRY_RUN = "DRY_RUN"
    ORPHAN_QUERY = "ORPHAN_QUERY"


class ExperimentOutcome(BaseModel):
    refuted: StrictBool = Field(description="True if prediction failed.")
    evidence_hash: str = Field(pattern=r"^[a-fA-F0-9]{64}$", description="Hash of the test execution log.")

    model_config = ConfigDict(extra="forbid")


class ExperimentSchemaL4(BaseModel):
    experiment_id: UUID
    prediction_id: UUID
    execution_context: ExecutionContext
    outcome: ExperimentOutcome

    model_config = ConfigDict(extra="forbid")
