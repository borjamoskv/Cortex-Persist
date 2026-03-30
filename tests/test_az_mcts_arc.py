"""
End-to-end verification for AlphaZero MCTS on ARC environment.
"""

import pytest
from cortex.engine.alphazero.mcts_core import MCTS, AlphaZeroNode
from cortex.engine.alphazero.network import LocalHeuristicNetwork
from cortex.engine.alphazero.arc_env import ARCEnv, ARCState

def test_mcts_simulation_arc_flow():
    # 1. Setup
    from cortex.agents.arc_agi_3.ingestion import GestaltNode, Pixel
    env = ARCEnv()
    network = LocalHeuristicNetwork(env)
    mcts = MCTS(network, num_simulations=10)
    
    # 2. Initial State: 2x2 grid with one node
    node = GestaltNode(id="n1", color=1, pixels={Pixel(0,0,1)}, bbox=(0,0,0,0))
    initial_state = ARCState(
        nodes=(node,),
        rows=2,
        cols=2,
        background=0,
        step_count=0
    )
    root = AlphaZeroNode(state=initial_state)
    
    # 3. Simulate
    # Should not crash and should populate visit counts
    mcts.simulate(root, env)
    
    # 4. Assertions
    assert root.visit_count == 10
    assert len(root.children) > 0
    
    probs = mcts.get_action_probabilities(root)
    assert len(probs) > 0
    assert abs(sum(probs.values()) - 1.0) < 1e-6

def test_arc_step_execution():
    env = ARCEnv()
    from cortex.agents.arc_agi_3.ingestion import GestaltNode, Pixel
    node = GestaltNode(id="node1", color=1, pixels={Pixel(0,0,1)}, bbox=(0,0,0,0))
    state = ARCState(nodes=(node,), rows=2, cols=2, background=0, step_count=0)
    
    # Action: Move node1 (0,0) down (1,0)
    from cortex.engine.alphazero.arc_env import ARCAction
    action = ARCAction(op="MOVE", node_id="node1", dr=1, dc=0)
    
    next_state = env.step(state, action)
    
    assert len(next_state.nodes) == 1
    assert next_state.step_count == 1
    # Check if node moved
    # Note: pixels in GestaltNode are Pixel objects
    px = list(next_state.nodes[0].pixels)[0]
    assert px.r == 1
    assert px.c == 0
