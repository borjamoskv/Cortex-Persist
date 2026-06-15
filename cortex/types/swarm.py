from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

TaskKind = Literal["reason", "retrieve", "plan", "execute", "audit", "summarize", "memory"]


class AgentCapabilityModel(BaseModel):
    name: str = Field(..., max_length=100)
    kinds: list[TaskKind] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    priority: int = 0
    max_concurrent: int = 1


# Capacidades reconocidas como kinds de routing duro.
# Ampliar aquí sin cambiar la lógica de resolución.
_ROUTING_KINDS: frozenset[str] = frozenset(
    {
        "audit",
        "reason",
        "memory",
        "search",
        "code",
        "translate",
        "summarize",
        "classify",
    }
)


class AgentRegisterRequestV2(BaseModel):
    """
    V2 del contrato de registro.
    capabilities → kinds (routing duro).
    tags         → semántica blanda, no participa en resolución.
    """

    name: str = Field(..., min_length=1, max_length=128)
    agent_type: str = Field(..., description="Tipo de agente: external | local | hybrid")
    public_key: str | None = Field(None)
    capabilities: list[str] = Field(
        default_factory=list,
        description="Capacidades funcionales. Se filtran contra _ROUTING_KINDS → kinds.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Etiquetas semánticas. Solo para búsqueda/filtrado, nunca routing.",
    )
    priority: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Prioridad de resolución. Mayor → preferido sobre handlers locales.",
    )

    # ── derivados ────────────────────────────────────────────────────
    kinds: list[str] = Field(default_factory=list, exclude=True)

    @model_validator(mode="after")
    def _derive_kinds(self) -> AgentRegisterRequestV2:
        """Filtra capabilities contra el set de routing duro y puebla kinds."""
        self.kinds = [c for c in self.capabilities if c in _ROUTING_KINDS]
        return self


class SubagentRequestModel(BaseModel):
    task_id: str
    kind: TaskKind
    target_agent: str = ""
    prompt: str
    context: dict[str, Any] = Field(default_factory=dict)
    parent_task_id: Optional[str] = None
    timeout_ms: int = 30_000
    max_retries: int = 1
    require_capability: Optional[str] = None


class SubagentResponseModel(BaseModel):
    task_id: str
    ok: bool
    target_agent: str
    output: Any = None
    error: Optional[str] = None
    trace: dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[float] = None
