"""CORTEX v8 — Neuromorphic Pipeline Orchestrator.

Wires the 6 core memory subsystems into a coherent cognitive pipeline:

  Query Path:
    SchemaEngine (top-down bias) → EpistemicVoidDetector → MetamemoryMonitor (FOK/JOL)

  Store Path:
    SchemaEngine (encoding filter) → Valence tagging → SystemsConsolidator (dual-trace)
    → STDPEngine (co-activation plasticity)

Pure Python, no I/O — delegates to existing components.
Each subsystem remains independently testable; the pipeline is glue.

DERIVATION: Ω₂ (Entropic Asymmetry — net negative entropy per operation)
           + Ω₄ (Aesthetic Integrity — ugly = incomplete integration)
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


# ─── Result Models ───────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class QueryResult:
    """Result of a full neuromorphic query assessment.

    Combines epistemic analysis, metacognitive judgment, and schema context
    into a single decision object that downstream code can act on.
    """

    epistemic: EpistemicAnalysis
    judgment: MetaJudgment
    fok_directive: FOKDirective
    schema_applied: str | None = None
    augmented_query: str = ""
    pipeline_ms: float = 0.0

    @property
    def safe_to_respond(self) -> bool:
        """Conservative gate: only respond if BOTH epistemic + metacognitive agree."""
        return (
            self.epistemic.is_safe_to_respond and self.fok_directive != FOKDirective.EXTERNAL_SEARCH
        )

    @property
    def should_search_more(self) -> bool:
        """The system believes knowledge exists but retrieval was insufficient."""
        return self.fok_directive == FOKDirective.RETRIEVE_WITH_VERIFICATION


@dataclass(frozen=True, slots=True)
class StoreResult:
    """Result of processing content through the store pipeline."""

    valence: ValenceRecord
    schema_applied: str | None = None
    filtered_content: str = ""
    stdp_edges_updated: int = 0
    pipeline_ms: float = 0.0


# ─── Pipeline Engine ─────────────────────────────────────────────────


class NeuromorphicPipeline:
    """Orchestrates the neuromorphic memory subsystems.

    Designed as a stateless coordinator — all state lives in the
    individual subsystems (MetamemoryMonitor, STDPEngine, etc.).

    Usage::

        pipeline = NeuromorphicPipeline()

        # Query assessment
        result = pipeline.assess_query(
            query="How does CORTEX handle encryption?",
            query_embedding=[0.1, 0.2, ...],
            candidates=[...],
        )
        if result.safe_to_respond:
            ...  # formulate response

        # Store processing
        result = pipeline.process_store(
            content="Decided to use AES-256-GCM for fact encryption",
            fact_type="decision",
            fact_id="fact_123",
        )
    """

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

    # ── Query Path ────────────────────────────────────────────────

    def assess_query(
        self,
        query: str,
        query_embedding: list[float],
        candidates: list[dict[str, Any]],
        *,
        engrams: list[Any] | None = None,
    ) -> QueryResult:
        """Full neuromorphic query assessment.

        Pipeline:
          1. SchemaEngine: detect active schema, augment query
          2. EpistemicVoidDetector: analyze search result topology
          3. MetamemoryMonitor: FOK/JOL introspection

        Args:
            query: Raw query text.
            query_embedding: Query vector for FOK assessment.
            candidates: Search results as dicts with 'score', 'content', 'id'.
            engrams: Optional engram objects for metamemory (if available).
        """
        t0 = time.monotonic()

        # Step 1: Schema detection + query augmentation
        schema = self._schema_engine.match_schema(query)
        augmented = query
        schema_name: str | None = None
        if schema:
            augmented = self._schema_engine.apply_retrieval_schema(schema, query)
            schema_name = schema.name

        # Step 2: Epistemic void detection on raw search results
        epistemic = self._void_detector.analyze(candidates)

        # Step 3: Metacognitive introspection
        engram_list = engrams or []
        judgment = self._metamemory.introspect(
            query_embedding=query_embedding,
            candidate_engrams=engram_list,
            retrieval_score=epistemic.top_similarity,
        )

        # Step 4: FOK directive
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
        """Feed retrieval outcomes back to the metamemory calibration system."""
        self._metamemory.record_outcome(
            RetrievalOutcome(
                query=query,
                project_id=project_id,
                predicted_confidence=predicted_confidence,
                actual_success=actual_success,
                retrieval_score=retrieval_score,
            )
        )

    # ── Store Path ────────────────────────────────────────────────

    def process_store(
        self,
        content: str,
        fact_type: str = "",
        fact_id: str = "",
        related_fact_ids: list[str] | None = None,
    ) -> StoreResult:
        """Process content through the store pipeline before persistence.

        Pipeline:
          1. SchemaEngine: detect schema, apply encoding filter
          2. Valence: classify emotional charge
          3. STDP: record co-activation with related facts

        Args:
            content: Raw fact content to store.
            fact_type: CORTEX fact type (decision, error, bridge, etc).
            fact_id: Unique ID for STDP co-activation tracking.
            related_fact_ids: Other facts co-activated with this one.
        """
        t0 = time.monotonic()

        # Step 1: Schema-guided encoding
        schema = self._schema_engine.match_schema(content)
        filtered = content
        schema_name: str | None = None
        if schema:
            filtered = self._schema_engine.apply_encoding_schema(schema, content)
            schema_name = schema.name

        # Step 2: Emotional valence classification
        valence = classify_valence(content, fact_type)

        # Step 3: STDP co-activation (strengthens edges between related concepts)
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

    # ── Accessors ─────────────────────────────────────────────────

    @property
    def metamemory(self) -> MetamemoryMonitor:
        """Direct access to the metamemory monitor for calibration reports."""
        return self._metamemory

    @property
    def stdp(self) -> STDPEngine:
        """Direct access to the STDP engine for graph inspection."""
        return self._stdp

    @property
    def calibration_score(self) -> float:
        """Brier score of confidence predictions. Lower = better."""
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
