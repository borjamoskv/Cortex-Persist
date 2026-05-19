"""
CORTEX v8 — Neuromorphic Pipeline (Pre-Query & Pre-Store Cognitive Gateway).

Orchestrates the cognitive assessment layer that wraps every memory operation:

  Query path:  SchemaEngine → EpistemicVoidDetector → MetamemoryMonitor → QueryResult
  Store path:  SchemaEngine → ValenceClassifier → STDPEngine → StoreResult

The pipeline is the single entry-point for all memory I/O that requires
epistemic evaluation, emotional tagging, or synaptic reinforcement.

Derivation: Ω₃ (Byzantine Default) + Ω₂ (Entropic Asymmetry)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from cortex.memory.metamemory import (
    FOKDirective,
    MetaJudgment,
    MetamemoryMonitor,
    RetrievalOutcome,
)
from cortex.memory.schemas import SchemaEngine
from cortex.memory.stdp import STDPEngine
from cortex.memory.valence import ValenceRecord, classify_valence
from cortex.memory.void_detector import (
    EpistemicAnalysis,
    EpistemicVoidDetector,
)

logger = logging.getLogger("cortex.memory.pipeline")


@dataclass(frozen=True)
class QueryResult:
    epistemic: EpistemicAnalysis
    judgment: MetaJudgment
    fok_directive: FOKDirective
    schema_applied: str | None = None
    augmented_query: str = ""
    pipeline_ms: float = 0.0

    @property
    def safe_to_respond(self) -> bool:
        return (
            self.epistemic.is_safe_to_respond and self.fok_directive != FOKDirective.EXTERNAL_SEARCH
        )

    @property
    def should_search_more(self) -> bool:
        return self.fok_directive == FOKDirective.RETRIEVE_WITH_VERIFICATION


@dataclass(frozen=True)
class StoreResult:
    valence: ValenceRecord
    schema_applied: str | None = None
    filtered_content: str = ""
    stdp_edges_updated: int = 0
    pipeline_ms: float = 0.0


class NeuromorphicPipeline:
    __slots__ = ("_metamemory", "_void_detector", "_schema_engine", "_stdp")

    def __init__(
        self,
        metamemory: MetamemoryMonitor | None = None,
        void_detector: EpistemicVoidDetector | None = None,
        schema_engine: SchemaEngine | None = None,
        stdp: STDPEngine | None = None,
    ) -> None:
        self._metamemory = metamemory or MetamemoryMonitor()
        self._void_detector = void_detector or EpistemicVoidDetector()
        self._schema_engine = schema_engine or SchemaEngine()
        self._stdp = stdp or STDPEngine()

    def assess_query(
        self,
        query: str,
        query_embedding: list[float],
        candidates: list[dict[str, Any]],
        *,
        engrams: list[Any] | None = None,
    ) -> QueryResult:
        t0 = time.monotonic()

        schema = self._schema_engine.match_schema(query)
        augmented = self._schema_engine.apply_retrieval_schema(schema, query) if schema else query
        schema_name = schema.name if schema else None

        epistemic = self._void_detector.analyze(candidates)

        engram_list = engrams or []
        judgment = self._metamemory.introspect(
            query_embedding=query_embedding,
            candidate_engrams=engram_list,
            retrieval_score=epistemic.top_similarity,
        )

        directive = self._metamemory.fok_recommendation(judgment.fok_score)

        elapsed = (time.monotonic() - t0) * 1000

        return QueryResult(
            epistemic=epistemic,
            judgment=judgment,
            fok_directive=directive,
            schema_applied=schema_name,
            augmented_query=augmented,
            pipeline_ms=round(elapsed, 2),
        )

    def record_retrieval_outcome(
        self,
        query: str,
        predicted_confidence: float,
        actual_success: bool,
        project_id: str = "default_project",
        retrieval_score: float = 0.0,
    ) -> None:
        self._metamemory.record_outcome(
            RetrievalOutcome(
                query=query,
                project_id=project_id,
                predicted_confidence=predicted_confidence,
                actual_success=actual_success,
                retrieval_score=retrieval_score,
            )
        )

    def process_store(
        self,
        content: str,
        fact_type: str = "",
        fact_id: str = "",
        related_fact_ids: list[str] | None = None,
    ) -> StoreResult:
        t0 = time.monotonic()

        schema = self._schema_engine.match_schema(content)
        filtered = self._schema_engine.apply_encoding_schema(schema, content) if schema else content
        schema_name = schema.name if schema else None

        valence = classify_valence(content, fact_type)

        edges_updated = 0
        if fact_id:
            self._stdp.record_activation(fact_id)
            edges_updated += 1
            for related_id in related_fact_ids or []:
                self._stdp.record_activation(related_id)
                edges_updated += 1

        elapsed = (time.monotonic() - t0) * 1000

        return StoreResult(
            valence=valence,
            schema_applied=schema_name,
            filtered_content=filtered,
            stdp_edges_updated=edges_updated,
            pipeline_ms=round(elapsed, 2),
        )

    @property
    def metamemory(self) -> MetamemoryMonitor:
        return self._metamemory

    @property
    def stdp(self) -> STDPEngine:
        return self._stdp

    @property
    def calibration_score(self) -> float:
        return self._metamemory.calibration_score()

    def __repr__(self) -> str:
        cal = self.calibration_score
        cal_str = f"{cal:.3f}" if cal >= 0 else "insufficient_data"
        return (
            f"NeuromorphicPipeline("
            f"calibration={cal_str}, "
            f"stdp_edges={self._stdp.edge_count}, "
            f"stdp_nodes={self._stdp.node_count})"
        )
