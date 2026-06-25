import pytest
import os
import json
import asyncio
from pathlib import Path
from cortex.extensions.ouroboros_mythos.ouroboros_loop import MythosOuroborosEngine

@pytest.mark.asyncio
async def test_ouroboros_physical_transition_cycle(tmp_path):
    # Setup temporary security log path
    log_file = tmp_path / "security_audit_log.jsonl"
    
    # Initialize the engine
    engine = MythosOuroborosEngine(log_path=str(log_file))
    
    assert engine.state.cycle_count == 0
    assert engine.state.state_hash == 0
    
    # 1. Observe
    obs = await engine._observe()
    assert isinstance(obs["cpu_pct_scaled"], int)
    assert isinstance(obs["ram_pct_scaled"], int)
    assert isinstance(obs["latency_ms"], int)
    
    # 2. Diagnose
    diag = await engine._diagnose(obs)
    assert "anomaly" in diag
    
    # 3. Plan
    plan = await engine.planner.synthesize_plan(diag)
    assert "steps" in plan
    assert isinstance(plan["expected_exergy_units"], int)
    
    # 4. Act
    action_result = await engine._act(plan)
    assert action_result["status"] == "success"
    assert isinstance(action_result["action_type"], bytes)
    
    # 5. Critic
    critic_score = await engine._criticize(action_result)
    assert isinstance(critic_score, int)
    assert 0 <= critic_score <= 100
    
    # 6. Exergy Yield calculation
    exergy_yield = engine.exergy.compute_yield(reward=critic_score)
    assert isinstance(exergy_yield, int)
    
    # 7. Memorize and State Commit
    if exergy_yield > 0:
        await engine.memory.store_episodic(action_result, critic_score)
        engine.state.commit_state_hash(action_result)
        
        # Log to ledger
        action_name = action_result["action_type"].decode("utf-8")
        await engine.ledger.log_action(
            tenant_id="C5-REAL-MYTHOS-1",
            actor_role="OuroborosNode",
            actor_id="mythos-agent-01",
            action=action_name,
            resource="hardware_sensors",
            status="SUCCESS",
            state_diff=f"exergy_yield={exergy_yield};critic_score={critic_score}"
        )
        
        # Wait for the async ledger batch worker to flush queue to file
        await asyncio.sleep(0.1)
        
        # Verify state mutation
        assert engine.state.cycle_count == 1
        assert engine.state.state_hash != 0
        
        # Verify ledger file content
        assert log_file.exists()
        with open(log_file) as f:
            lines = f.readlines()
            assert len(lines) > 0
            first_event = json.loads(lines[0])
            assert first_event["payload"]["action"] == action_name
            assert first_event["payload"]["tenant_id"] == "C5-REAL-MYTHOS-1"
