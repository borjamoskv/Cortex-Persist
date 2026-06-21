import torch
import torch.nn as nn

class PolicyNet(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        # BABYLON-60 Epistemology: Deterministic architecture scaling
        self.net = nn.Sequential(
            nn.Linear(dim, 256),
            nn.ReLU(),
            nn.Linear(256, dim)
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """Forward pass emitting stochastic action distribution."""
        return torch.softmax(self.net(state), dim=-1)
