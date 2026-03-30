"""
Gestalt Extraction Engine
Translates ARC grids into Object-Centric Representations (Nodes).
"""

from dataclasses import dataclass
from typing import List, Tuple, Set

@dataclass
class Node:
    """A contiguous block of identical color in the ARC grid."""
    color: int
    pixels: Set[Tuple[int, int]]  # (row, col)
    
    @property
    def box(self):
        rows = [r for r, c in self.pixels]
        cols = [c for r, c in self.pixels]
        return min(rows), max(rows), min(cols), max(cols)

class GestaltGraph:
    """Object-Centric Representation of an ARC grid."""
    def __init__(self, grid: List[List[int]]):
        self.height = len(grid)
        self.width = len(grid[0]) if self.height else 0
        self.nodes: List[Node] = self._extract_nodes(grid)
        self.bg_color = 0

    def _extract_nodes(self, grid: List[List[int]]) -> List[Node]:
        nodes = []
        visited = set()
        
        for r in range(self.height):
            for c in range(self.width):
                if (r, c) not in visited and grid[r][c] != 0:
                    pixels = self._flood_fill(grid, r, c, visited)
                    nodes.append(Node(color=grid[r][c], pixels=pixels))
        return nodes

    def _flood_fill(self, grid, r, c, visited) -> Set[Tuple[int, int]]:
        color = grid[r][c]
        pixels = set()
        stack = [(r, c)]
        
        while stack:
            curr_r, curr_c = stack.pop()
            if (curr_r, curr_c) in visited:
                continue
            if not (0 <= curr_r < self.height and 0 <= curr_c < self.width):
                continue
            if grid[curr_r][curr_c] != color:
                continue
                
            visited.add((curr_r, curr_c))
            pixels.add((curr_r, curr_c))
            
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                stack.append((curr_r + dr, curr_c + dc))
                
        return pixels

    def render(self) -> List[List[int]]:
        """Render the graph back to a 2D grid."""
        grid = [[self.bg_color for _ in range(self.width)] for _ in range(self.height)]
        for node in self.nodes:
            for r, c in node.pixels:
                if 0 <= r < self.height and 0 <= c < self.width:
                    grid[r][c] = node.color
        return grid
