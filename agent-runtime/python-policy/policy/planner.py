import torch
from .mcts import rollout

def generate_actions(state: torch.Tensor) -> list[str]:
    """Action space generator. To be synced with Rust Action Enum."""
    return ["OBSERVE", "MUTATE_DOM", "WRITE_LKRGSER", "EXEC_BASH", "AWAIT"]

def apply_mock(state: torch.Tensor, action: str) -> torch.Tensor:
    """Mock state transition for planning."""
    return state + torch.randn_like(state) * 0.05

def plan(state: torch.Tensor, policy_net, value_net) -> list[tuple[str, float]]:
    """Sanedrín Real Planner. Scores candidate actions via MCTS rollouts."""
    candidates = generate_actions(state)
    
    scored = []
    for a in candidates:
        # Evaluate simulated future trajectory
        sim_state = apply_mock(state, a)
        v = rollout(sim_state, policy_net, value_net, depth=5)
        scored.append((a, v))

    # Sort by descending value
    scored.sort(key=lambda x: x[1], reverse=True)
    
    # Return top 5 actions (DeepMind-style truncation)
    return scored[:5]
