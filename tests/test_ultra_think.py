from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.extensions.hypervisor.belief_object import (
    BeliefConfidence,
    BeliefObject,
    BeliefStatus,
    VerdictAction,
)
from cortex.extensions.llm.cognitive_handoff import CognitiveHandoff, _AuditResult
from cortex.utils.result import Ok


@pytest.mark.asyncio
async def test_ultra_think_escalation_on_p0():
    # Setup mocks
    mock_router = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.get_llm_router = AsyncMock(return_value=mock_router)

    handoff = CognitiveHandoff(router=mock_router, engine=mock_engine)

    # Create a P0 critical belief
    belief = BeliefObject(
        id="p0-test",
        content="System core collapse imminent. Execute rewrite.",
        confidence=BeliefConfidence.C5_AXIOMATIC,
        status=BeliefStatus.ACTIVE,
        project="test",
        metadata={"p0_critical": True},
    )

    # Mock generation and audit results
    mock_router.execute_resilient.side_effect = [
        Ok("```python\nprint('hello')\n```"),  # Initial proposal
        Ok("OK"),  # Logic audit
    ]

    # Mock infrastructure prescreen and auditors to pass
    handoff._infra_prescreen = AsyncMock(return_value=MagicMock(action="audit", tokens_used=0))
    handoff._auditor_economic_verify = AsyncMock(
        return_value=_AuditResult(verdict="CERTAIN", has_contradiction=False, tokens_used=0)
    )

    # Execute
    verdict = await handoff.process_belief(belief)

    # Verify
    assert verdict.model == "ultra_think"
    assert verdict.action == VerdictAction.ACCEPT
    assert handoff._ultra_think_count == 1


@pytest.mark.asyncio
async def test_ultra_think_detonation_on_ast_failure():
    # Setup mocks
    mock_router = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.get_llm_router = AsyncMock(return_value=mock_router)

    handoff = CognitiveHandoff(router=mock_router, engine=mock_engine)

    # Create a P0 critical belief
    belief = BeliefObject(
        id="p0-ast-fail",
        content="Fix this code ghost.",
        confidence=BeliefConfidence.C4_CONFIRMED,
        status=BeliefStatus.ACTIVE,
        project="test",
        metadata={"p0_critical": True},
    )

    # Mock proposal with INVALID python code
    mock_router.execute_resilient.side_effect = [
        Ok("```python\ndef fail: missing paren\n```"),  # Initial proposal
        Ok("OK"),  # Logic audit
    ]

    handoff._infra_prescreen = AsyncMock(return_value=MagicMock(action="audit", tokens_used=0))
    handoff._auditor_economic_verify = AsyncMock(
        return_value=_AuditResult(verdict="CERTAIN", has_contradiction=False, tokens_used=0)
    )

    # Execute
    verdict = await handoff.process_belief(belief)

    # Verify
    assert verdict.model == "ultra_think"
    assert verdict.action == VerdictAction.QUARANTINE
    assert "AST Validation failed" in verdict.reason
