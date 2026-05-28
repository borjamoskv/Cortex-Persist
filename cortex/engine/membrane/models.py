import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MembraneLogLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class MembraneLog(BaseModel):
    """
    Audit Trail entry indicating what was stripped from a raw engram
    to ensure compliance and purity. Immutable by design.
    """

    timestamp: float = Field(default_factory=time.time)
    original_size_bytes: int
    purified_size_bytes: int = 0
    pii_stripped: bool = False
    paths_obfuscated: bool = False
    tracebacks_pruned: bool = False
    level: MembraneLogLevel = MembraneLogLevel.INFO
    details: str | None = None


class PureEngram(BaseModel):
    """
    A strictly validated, Zero-Trust data structure representing a memory.
    Extra fields are forbidden to prevent causal state poisoning (Byzantine Default).
    """

    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., description="The type of memory: decision, error, ghost, bridge")
    source: str = Field(..., description="The origin of this memory, e.g., agent:gemini")
    topic: str = Field(..., description="The project or primary topic this memory belongs to")
    content: str = Field(..., description="The actual purified content or logic")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional verified context"
    )
    original_raw_hash: str | None = Field(
        None, description="SHA-256 hash of the payload before digestion"
    )
    log: MembraneLog | None = Field(None, description="Audit trail of the purification process")
