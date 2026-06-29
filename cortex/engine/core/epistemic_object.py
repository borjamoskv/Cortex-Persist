# [C5-REAL] Exergy-Maximized
"""Epistemic Object Model (CEP-001).

Immutable core entities representing the atoms of knowledge in the DAG.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar, Literal

from cortex.engine.core.canonical import compute_object_hash


@dataclass(frozen=True)
class EpistemicObject:
    """Base primitive for all knowledge items. Immutable & Content-Addressed."""
    # Type tag used for hashing prefix (overridden by subclasses)
    TYPE_TAG: ClassVar[str] = "EpistemicObject"

    @property
    def identifier(self) -> str:
        """The SHA3-256 canonical hash of the object's content."""
        # We must exclude 'identifier' from serialization if it was stored,
        # but since it's a property, asdict() doesn't include it.
        return compute_object_hash(self.TYPE_TAG, asdict(self))


@dataclass(frozen=True)
class Assertion(EpistemicObject):
    """A logical or factual claim about reality."""
    TYPE_TAG: ClassVar[str] = "Assertion"
    data: Any


@dataclass(frozen=True)
class Evidence(EpistemicObject):
    """A raw fragment of observable data."""
    TYPE_TAG: ClassVar[str] = "Evidence"
    data: Any


@dataclass(frozen=True)
class Constraint(EpistemicObject):
    """A rule of logical invariance."""
    TYPE_TAG: ClassVar[str] = "Constraint"
    rule_type: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class SupportRelation(EpistemicObject):
    """The immutable causal link between two objects."""
    TYPE_TAG: ClassVar[str] = "SupportRelation"
    evidence_id: str
    assertion_id: str
    relation_type: Literal["SUPPORTS", "REFUTES", "OBSERVES", "DERIVED_FROM", "CONTRADICTS"]


@dataclass(frozen=True)
class Annotation:
    """Metadata decoupled from the core semantic model."""
    key: str
    namespace: str
    value: str
    value_type: Literal["String", "JSON", "CBOR"]
    issuer: str
    signature: bytes


@dataclass(frozen=True)
class ProposedState:
    """A bundle of objects and relations submitted for validation."""
    objects: dict[str, dict[str, Any]] = field(default_factory=dict)
