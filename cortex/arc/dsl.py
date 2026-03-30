"""
ARC Domain-Specific Language (DSL) Primitives.
These functions define the physical boundaries for LLM synthesis.
"""

from typing import List
from .gestalt import GestaltGraph, Node

def move_node(graph: GestaltGraph, node: Node, d_row: int, d_col: int):
    """
    Translates a node by (d_row, d_col). 
    Pixels that move out of bounds are discarded or clipped depending on the ARC game semantics.
    For now, simply mutate the node's pixel coordinates.
    """
    new_pixels = set()
    for r, c in node.pixels:
        # Simple translation without collision check for MVP
        new_pixels.add((r + d_row, c + d_col))
    node.pixels = new_pixels

def recolor_node(graph: GestaltGraph, node: Node, new_color: int):
    """Mutates the color of a target node."""
    node.color = new_color

def filter_by_color(graph: GestaltGraph, color: int) -> List[Node]:
    """Returns all nodes matching the given color."""
    return [n for n in graph.nodes if n.color == color]

# The restricted environment globals for evaluating LLM synthesized programs
DSL_ENVIRONMENT = {
    "move_node": move_node,
    "recolor_node": recolor_node,
    "filter_by_color": filter_by_color,
}
