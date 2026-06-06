# [C5-REAL] Exergy-Maximized
from dataclasses import dataclass, field
from typing import Any

from cortex.interfaces.memory_provider import MemoryProvider, MemorySubgraph
from cortex.semantic.hybrid_retriever import HybridRetriever
from cortex.semantic.intent_encoder import IntentEncoder
from cortex.worker.issue_reader import IssueContext, IssueReader


@dataclass
class TriageContext:
    issue: IssueContext
    memory_subgraph: MemorySubgraph
    architecture_context: list[Any] = field(default_factory=list)


class SemanticAttentionOrchestrator:
    """
    Sprint 3: Semantic Attention Orchestrator (formerly IssueTriagePipeline).
    Orchestrates Intent Encoding -> Hybrid Retrieval (Vector + Graph) -> Coherence.
    """

    def __init__(self, memory_provider: MemoryProvider):
        self.memory = memory_provider
        self.intent_encoder = IntentEncoder(memory_provider)
        self.retriever = HybridRetriever(memory_provider)

    def process(self, issue_url: str) -> TriageContext:
        # Step 1: Deterministic Extraction
        issue = IssueReader.read(issue_url)

        # Step 2: Formulate the query for semantic traversal
        query = f"Title: {issue.title}\nDescription: {issue.body}"

        # Step 3: Intent Encoding (Semantic + Temporal + Abstraction biases)
        intent = self.intent_encoder.encode(query)

        # Step 4: Hybrid Retrieval -> Graph Expansion -> Coherence Scoring -> Late Hydration
        memory_subgraph = self.retriever.retrieve(
            query=query,
            intent=intent,
            k=10,  # Max 10 nodes for final hydration
        )

        return TriageContext(
            issue=issue,
            memory_subgraph=memory_subgraph,
        )
