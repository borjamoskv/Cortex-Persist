# [C5-REAL] Exergy-Maximized
"""CORTEX E2E Pipeline - Integration Tests.

Tests the full pipeline flow: Ingress → Context → Plan → Execute → Persist → Egress.
"""

import pytest
import time

from babylon60.pipeline import (
    ContextPacket,
    DeliveryTarget,
    DeliveryType,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    PipelineStatus,
    StageTrace,
)
from babylon60.pipeline.orchestrator import CortexOrchestrator
from babylon60.pipeline._orchestrator_exceptions import (
    BudgetExhaustedError,
    PipelineCancelledError,
)
from babylon60.router.router import AgentRouter, AgentCapability
from babylon60.context.assembler import ContextAssembler
from babylon60.delivery.manager import DeliveryManager


# ── Context Assembler Tests ──


class TestContextAssembler:
    """Test the unified context assembler."""

    def test_empty_assembly(self, tmp_path):
        assembler = ContextAssembler(knowledge_dir=tmp_path)
        ctx = assembler.assemble(intent="test query")
        assert isinstance(ctx, ContextPacket)
        assert ctx.total_tokens == 0

    def test_hint_resolution_missing_ki(self, tmp_path):
        assembler = ContextAssembler(knowledge_dir=tmp_path)
        ctx = assembler.assemble(intent="test", hints=["nonexistent_ki_12345"])
        assert len(ctx.knowledge_items) == 0  # Should not crash

    def test_filesystem_knowledge_scan(self, tmp_path, monkeypatch):
        ki_dir = tmp_path / "knowledge"
        ki_dir.mkdir()

        # Create matching file
        matching_file = ki_dir / "quantum_computing.md"
        matching_file.write_text("Quantum computers use qubits instead of bits.", encoding="utf-8")

        # Create non-matching file
        non_matching_file = ki_dir / "baking_bread.txt"
        non_matching_file.write_text("To bake sourdough bread, you need flour, water, and salt.", encoding="utf-8")

        # Monkeypatch KNOWLEDGE_DIR attribute
        import babylon60.context.assembler as assembler_mod
        monkeypatch.setattr(assembler_mod, "KNOWLEDGE_DIR", str(ki_dir))

        assembler = ContextAssembler()
        ctx = assembler.assemble(intent="tell me about quantum computing")

        # Verify quantum file matched
        assert len(ctx.knowledge_items) == 1
        assert ctx.knowledge_items[0]["source"] == "quantum_computing.md"
        assert "qubits" in ctx.knowledge_items[0]["content"]
        assert ctx.relevance_scores["quantum_computing.md"] > 0.0

    @pytest.mark.asyncio
    async def test_assemble_async(self, tmp_path):
        assembler = ContextAssembler(knowledge_dir=tmp_path)
        ctx = await assembler.assemble_async(intent="test query")
        assert isinstance(ctx, ContextPacket)
        assert ctx.total_tokens == 0

    def test_deduplication(self, tmp_path):
        assembler = ContextAssembler(knowledge_dir=tmp_path)
        ctx = ContextPacket()
        
        # Test adding duplicate source
        added1 = assembler._add_knowledge_item(ctx, "file.md", "hello world", "hint", 3, 1.0)
        added2 = assembler._add_knowledge_item(ctx, "file.md", "different content", "hint", 4, 1.0)
        assert added1 is True
        assert added2 is False
        assert len(ctx.knowledge_items) == 1

        # Test adding duplicate content
        added3 = assembler._add_knowledge_item(ctx, "other.md", "hello world", "hint", 3, 1.0)
        assert added3 is False
        assert len(ctx.knowledge_items) == 1

    def test_hint_direct_file(self, tmp_path):
        # Create a direct file under knowledge_dir
        direct_file = tmp_path / "my_direct_info.md"
        direct_file.write_text("Sovereign execution details", encoding="utf-8")

        assembler = ContextAssembler(knowledge_dir=tmp_path)
        ctx = assembler.assemble(intent="test", hints=["my_direct_info.md"])

        assert len(ctx.knowledge_items) == 1
        assert ctx.knowledge_items[0]["source"] == "my_direct_info.md"
        assert ctx.knowledge_items[0]["content"] == "Sovereign execution details"
        assert ctx.relevance_scores["my_direct_info.md"] == 1.0


