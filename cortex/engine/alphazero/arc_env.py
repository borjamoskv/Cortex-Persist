"""
ARC-AGI Environment Wrapper for AlphaZero Self-Play.
"""

from dataclasses import dataclass
from typing import Any

from cortex.agents.arc_agi_3.ingestion import GestaltNode, reconstruct_grid
from cortex.agents.arc_agi_3.dsl import (
    move_node,
    recolor_node,
    rotate_node_90,
    flip_node_h,
    flip_node_v,
)

@dataclass(frozen=True)
class ARCAction:
    op: str  # 'MOVE', 'RECOLOR', 'ROTATE', 'FLIP_H', 'FLIP_V'
    node_id: str
    dr: int = 0
    dc: int = 0
    color: int = 0


@dataclass(frozen=True)
class ARCState:
    nodes: tuple[GestaltNode, ...]
    rows: int
    cols: int
    background: int
    target_grid: tuple[tuple[int, ...], ...] | None = None
    step_count: int = 0


class ARCEnv:
    """
    Markov Decision Process wrapper for ARC-AGI.
    Maps MCTS actions to DSL operations and evaluates against the target grid.
    """

    MAX_STEPS = 10

    @staticmethod
    def _grid_to_tuple(grid: list[list[int]]) -> tuple[tuple[int, ...], ...]:
        return tuple(tuple(row) for row in grid)

    def get_legal_actions(self, state: ARCState) -> list[ARCAction]:
        """Generate legal actions from the current state."""
        if state.step_count >= self.MAX_STEPS:
            return []
            
        actions = []
        for node in state.nodes:
            # Recolor
            for c in range(10):
                if c != node.color:
                    actions.append(ARCAction(op="RECOLOR", node_id=node.id, color=c))
            
            # Move (1 step cardinal)
            actions.append(ARCAction(op="MOVE", node_id=node.id, dr=-1, dc=0))
            actions.append(ARCAction(op="MOVE", node_id=node.id, dr=1, dc=0))
            actions.append(ARCAction(op="MOVE", node_id=node.id, dr=0, dc=-1))
            actions.append(ARCAction(op="MOVE", node_id=node.id, dr=0, dc=1))
            
            # Transforms
            actions.append(ARCAction(op="ROTATE", node_id=node.id))
            actions.append(ARCAction(op="FLIP_H", node_id=node.id))
            actions.append(ARCAction(op="FLIP_V", node_id=node.id))
            
        return actions

    def step(self, state: ARCState, action: ARCAction) -> ARCState:
        """Apply an action to the state and return the new state."""
        new_nodes = []
        for node in state.nodes:
            if node.id == action.node_id:
                if action.op == "MOVE":
                    new_nodes.append(move_node(node, action.dr, action.dc))
                elif action.op == "RECOLOR":
                    new_nodes.append(recolor_node(node, action.color))
                elif action.op == "ROTATE":
                    new_nodes.append(rotate_node_90(node))
                elif action.op == "FLIP_H":
                    new_nodes.append(flip_node_h(node))
                elif action.op == "FLIP_V":
                    new_nodes.append(flip_node_v(node))
            else:
                new_nodes.append(node)
                
        return ARCState(
            nodes=tuple(new_nodes),
            rows=state.rows,
            cols=state.cols,
            background=state.background,
            target_grid=state.target_grid,
            step_count=state.step_count + 1
        )

    def get_terminal_value(self, state: ARCState) -> float | None:
        """
        Check if the current state satisfies the target grid.
        Returns 1.0 for a win, -1.0 for a loss (max steps reached), or None if unresolved.
        """
        if state.target_grid is None:
            return None
            
        current_grid = reconstruct_grid(list(state.nodes), state.rows, state.cols, state.background)
        current_tuple = self._grid_to_tuple(current_grid)
        
        if current_tuple == state.target_grid:
            return 1.0  # Success
            
        if state.step_count >= self.MAX_STEPS:
            # We penalize failure to encourage finding the shortest path or aborting
            return -1.0
            
        return None
