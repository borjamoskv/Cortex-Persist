import torch
import torch.nn as nn

class ValueNet(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, 256),
            nn.ReLU(),
            nn.Linear(256, 1)
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """Evaluates epistemic/exergic value of a given state."""
        return self.net(state)
