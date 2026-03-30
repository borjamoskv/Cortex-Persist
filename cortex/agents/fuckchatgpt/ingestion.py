import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("cortex.agents.fuckchatgpt.ingestion")


@dataclass(frozen=True)
class Pixel:
    r: int
    c: int
    color: int

@dataclass
class GestaltNode:
    id: str
    pixels: set["Pixel"]
    color: int
    bbox: tuple[int, int, int, int]  # r_min, c_min, r_max, c_max
    
    @property
    def height(self) -> int:
        return self.bbox[2] - self.bbox[0] + 1
    
    @property
    def width(self) -> int:
        return self.bbox[3] - self.bbox[1] + 1

def extract_objects(grid: list[list[int]], background_color: int = 0) -> list[GestaltNode]:
    """
    Finds contiguous same-color blocks of pixels (4-connectivity).
    """
    rows = len(grid)
    if rows == 0:
        return []
    cols = len(grid[0])
    visited = set()
    objects = []
    
    def get_neighbors(r, c):
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                yield nr, nc

    obj_count = 0
    for r in range(rows):
        for c in range(cols):
            color = grid[r][c]
            if color != background_color and (r, c) not in visited:
                obj_pixels = set()
                stack = [(r, c)]
                visited.add((r, c))
                
                while stack:
                    curr_r, curr_c = stack.pop()
                    obj_pixels.add(Pixel(curr_r, curr_c, color))
                    
                    for nr, nc in get_neighbors(curr_r, curr_c):
                        if grid[nr][nc] == color and (nr, nc) not in visited:
                            visited.add((nr, nc))
                            stack.append((nr, nc))
                
                r_min = min(p.r for p in obj_pixels)
                r_max = max(p.r for p in obj_pixels)
                c_min = min(p.c for p in obj_pixels)
                c_max = max(p.c for p in obj_pixels)
                
                objects.append(GestaltNode(
                    id=f"obj_{obj_count}",
                    pixels=obj_pixels,
                    color=color,
                    bbox=(r_min, c_min, r_max, c_max)
                ))
                obj_count += 1
    return objects

def detect_global_gestalt(grid: list[list[int]]) -> dict[str, Any]:
    """Detects background (most frequent color) and basic grid properties."""
    rows = len(grid)
    if rows == 0:
        return {"rows": 0, "cols": 0, "background": 0, "unique_colors": []}
    cols = len(grid[0])
    
    counts = {}
    for r in range(rows):
        for c in range(cols):
            color = grid[r][c]
            counts[color] = counts.get(color, 0) + 1
    
    # Heuristic: background is usually the most frequent color, 
    # but color 0 is preferred if present and tied or significant.
    if counts:
        background = max(counts, key=counts.get) if counts else 0
    else:
        background = 0
        
    return {
        "rows": rows,
        "cols": cols,
        "background": background,
        "unique_colors": list(counts.keys())
    }

def reconstruct_grid(nodes: list[GestaltNode], rows: int, cols: int, background: int = 0) -> list[list[int]]:
    """Flatten nodes back into a 2D grid matrix."""
    grid = [[background for _ in range(cols)] for _ in range(rows)]
    for node in nodes:
        for p in node.pixels:
            if 0 <= p.r < rows and 0 <= p.c < cols:
                grid[p.r][p.c] = node.color
    return grid
