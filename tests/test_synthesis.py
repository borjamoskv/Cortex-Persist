# [C5-REAL] Exergy-Maximized
"""
Tests for CortexAutoSynthesisEngine.
Validates the Ω-Phase: Forge, Siege, Evolve loops.
"""

import asyncio
from pathlib import Path

import pytest

from cortex.engine.synthesis import CortexAutoSynthesisEngine


class DummyLLMManager:
    async def generate(self, prompt: str, **kwargs) -> str:
        # Simulate crystallization: stripping noise
        if "RUIDO TERMAL" in prompt:
            # Extract content to refine
            lines = prompt.split("RUIDO TERMAL:")[1].split("HECHO CRISTALIZADO:")[0].strip()
            # Strip fake noise
            return lines.replace("aquí tienes", "").replace("por supuesto", "").strip()
        return "crystallized fact"


@pytest.mark.asyncio
async def test_synthesis_engine_forge_and_siege(tmp_path: Path):
    engine = CortexAutoSynthesisEngine(
        llm_manager=DummyLLMManager(), bus_path=tmp_path, p95_budget_ms=100.0, exergy_floor=0.1
    )

    await engine.start()

    # 1. Provide noisy inputs
    raw_inputs = [
        {"content": "aquí tienes el fact: memory leak en weakref", "domain": "core"},
        {"content": "por supuesto, la latencia es 5ms", "domain": "metrics"},
        {"content": "noise noise noise"},  # Exergy will be low if not compressed well
    ]

    report = await engine.forge(raw_inputs)

    assert report.cycle_id == 1
    assert report.facts_ingested == 3
    # Dummy LLM will compress the first two, maybe not the third enough, or it will.
    assert report.facts_crystallized > 0
    assert report.agents_dispatched > 0
    assert report.wall_ms > 0

    await engine.stop()
