# [C5-REAL] Exergy-Maximized
"""Tests for the CausalClosureGuard."""

import pytest

from cortex.guards.causal_closure_guard import CausalClosureGuard, SwarmProposal


@pytest.fixture
def closure_guard() -> CausalClosureGuard:
    """Provides a guard configured with a lower threshold for testing."""
    return CausalClosureGuard(min_token_threshold=1000)


def test_empty_content_returns_false(closure_guard: CausalClosureGuard) -> None:
    """Empty content should be rejected but safely."""
    proposal = SwarmProposal(agent_id="test", mission_statement="test", content="   ")
    assert not closure_guard.verify_closure(proposal)


def test_low_token_cost_bypasses_strict_checks(closure_guard: CausalClosureGuard) -> None:
    """If the operation was cheap, it shouldn't be strictly penalized for missing structure."""
    proposal = SwarmProposal(
        agent_id="test",
        mission_statement="test",
        content="This is just some narrative text without code.",
        token_cost=500,  # Below 1000
    )
    # Should pass because it's cheap
    assert closure_guard.verify_closure(proposal)


def test_high_token_cost_with_code_block_passes(closure_guard: CausalClosureGuard) -> None:
    """A costly operation that outputs python code achieves causal closure."""
    content = """We evaluated the logic and synthesized this code:
```python
def my_invariant(): return True
```
"""
    proposal = SwarmProposal(
        agent_id="test", mission_statement="test", content=content, token_cost=5000
    )
    assert closure_guard.verify_closure(proposal)


def test_high_token_cost_with_ledger_payload_passes(closure_guard: CausalClosureGuard) -> None:
    """A costly operation that outputs a LedgerPayload achieves causal closure."""
    content = """Emitting to the audit trail:
LedgerPayload: { "tx": 123, "CORTEX-TAINT": "v1" }
"""
    proposal = SwarmProposal(
        agent_id="test", mission_statement="test", content=content, token_cost=5000
    )
    assert closure_guard.verify_closure(proposal)


def test_high_token_cost_without_structure_throws_saga_abort(
    closure_guard: CausalClosureGuard,
) -> None:
    """A costly operation that outputs only prose must be aborted as pure Anergy."""
    content = """I have thought deeply about this problem. 
The swarm has concluded that the best approach is to be careful and modular.
We should probably use a database to store things.
No code is needed at this time."""

    proposal = SwarmProposal(
        agent_id="test", mission_statement="test", content=content, token_cost=5000
    )

    with pytest.raises(RuntimeError) as exc_info:
        closure_guard.verify_closure(proposal)

    assert "Causal Closure" in str(exc_info.value)
    assert "AX-VIII Violation" in str(exc_info.value)


def test_causal_closure_guard_robust_json_array(closure_guard: CausalClosureGuard) -> None:
    """A costly operation with valid JSON array of dicts or python ast literal list of dicts should pass."""
    # 1. Standard JSON dict array
    proposal_json = SwarmProposal(
        agent_id="test",
        mission_statement="test",
        content='[{"key": "value", "nested": {"ok": true}}]',
        token_cost=5000,
    )
    assert closure_guard.verify_closure(proposal_json)

    # 2. Single quotes Python literal dict array (fails json.loads, passes ast.literal_eval)
    proposal_python = SwarmProposal(
        agent_id="test",
        mission_statement="test",
        content="[{'key': 'value', 'nested': {'ok': True}}]",
        token_cost=5000,
    )
    assert closure_guard.verify_closure(proposal_python)

    # 3. Non-dict list should fail
    proposal_invalid = SwarmProposal(
        agent_id="test",
        mission_statement="test",
        content="[1, 2, 3]",
        token_cost=5000,
    )
    with pytest.raises(RuntimeError):
        closure_guard.verify_closure(proposal_invalid)

    # 4. Empty list should fail
    proposal_empty = SwarmProposal(
        agent_id="test",
        mission_statement="test",
        content="[]",
        token_cost=5000,
    )
    with pytest.raises(RuntimeError):
        closure_guard.verify_closure(proposal_empty)


def test_causal_closure_guard_generic_code_blocks(closure_guard: CausalClosureGuard) -> None:
    """A costly operation with any generic code block should pass."""
    proposal_generic = SwarmProposal(
        agent_id="test",
        mission_statement="test",
        content="Here is some random data:\n```\nsome raw non-highlighted text\n```",
        token_cost=5000,
    )
    assert closure_guard.verify_closure(proposal_generic)

    proposal_js = SwarmProposal(
        agent_id="test",
        mission_statement="test",
        content="Here is some js:\n```javascript\nconsole.log(123);\n```",
        token_cost=5000,
    )
    assert closure_guard.verify_closure(proposal_js)
