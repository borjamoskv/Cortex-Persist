import torch
import random
from typing import Any, Callable

def simulate(state: torch.Tensor, action: Any) -> torch.Tensor:
    """Mock physics simulator for the MCTS rollout."""
    # In a C5-REAL environment, this should query the Rust Engine or a precise World Model
    # Here we apply a minimal stochastic permutation to the tensor.
    noise = torch.randn_like(state) * 0.01
    return state + noise

def sample(probs: torch.Tensor) -> int:
    """Sample action from distribution."""
    dist = torch.distributions.Categorical(probs)
    return dist.sample().item()

def rollout(state: torch.Tensor, policy_fn: Callable, value_fn: Callable, depth: int = 5) -> float:
    """Monte Carlo Tree Search Rollout (Lite)."""
    total_value = 0.0
    current = state

    for _ in range(depth):
        with torch.no_grad():
            probs = policy_fn(current)
            action = sample(probs)
            
            # Predict next state (World Model / Simulator)
            current = simulate(current, action)
            
            # Evaluate epistemic state
            val = value_fn(current)
            total_value += val.item()

    return total_value
