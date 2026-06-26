# [C5-REAL] Exergy-Maximized
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TaxFactPayload:
    action: str
    amount_eur: float
    tax_category: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaxFact:
    fact_type: str
    agent_id: str
    client_id: str
    period: str
    confidence: float
    payload: TaxFactPayload
    provenance_chain: list[str]
    human_override: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_type": self.fact_type,
            "agent_id": self.agent_id,
            "client_id": self.client_id,
            "period": self.period,
            "confidence": self.confidence,
            "payload": self.payload.to_dict(),
            "provenance_chain": self.provenance_chain,
            "human_override": self.human_override,
        }
