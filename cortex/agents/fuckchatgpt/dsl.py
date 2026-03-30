import logging

from .ingestion import GestaltNode, Pixel

logger = logging.getLogger("cortex.agents.fuckchatgpt.dsl")

def move_node(node: GestaltNode, dr: int, dc: int) -> GestaltNode:
    """Returns a new node shifted by (dr, dc)."""
    new_pixels = {Pixel(p.r + dr, p.c + dc, p.color) for p in node.pixels}
    r_min, c_min, r_max, c_max = node.bbox
    return GestaltNode(
        id=node.id,
        pixels=new_pixels,
        color=node.color,
        bbox=(r_min + dr, c_min + dc, r_max + dr, c_max + dc)
    )

def recolor_node(node: GestaltNode, new_color: int) -> GestaltNode:
    """Returns a new node with a different color."""
    new_pixels = {Pixel(p.r, p.c, new_color) for p in node.pixels}
    return GestaltNode(
        id=node.id,
        pixels=new_pixels,
        color=new_color,
        bbox=node.bbox
    )

def rotate_node_90(node: GestaltNode) -> GestaltNode:
    """Rotates the node 90 degrees clockwise around its top-left corner (0,0 relative)."""
    # 1. Translate to origin
    r_min, c_min, _, _ = node.bbox
    # 2. Rotate (r, c) -> (c, -r)
    # 3. Translate back but we need to recompute bbox
    rotated_pixels = set()
    for p in node.pixels:
        rel_r, rel_c = p.r - r_min, p.c - c_min
        new_rel_r, new_rel_c = rel_c, -rel_r
        rotated_pixels.add(Pixel(new_rel_r, new_rel_c, p.color))
        
    # Re-normalize to positive space or just shift back
    min_r = min(p.r for p in rotated_pixels)
    min_c = min(p.c for p in rotated_pixels)
    final_pixels = {Pixel(p.r - min_r + r_min, p.c - min_c + c_min, p.color) for p in rotated_pixels}
    
    # Recompute bbox
    nr_min = min(p.r for p in final_pixels)
    nr_max = max(p.r for p in final_pixels)
    nc_min = min(p.c for p in final_pixels)
    nc_max = max(p.c for p in final_pixels)
    
    return GestaltNode(
        id=f"{node.id}_rot",
        pixels=final_pixels,
        color=node.color,
        bbox=(nr_min, nc_min, nr_max, nc_max)
    )

def flip_node_h(node: GestaltNode) -> GestaltNode:
    """Flips the node horizontally across its center."""
    r_min, c_min, r_max, c_max = node.bbox
    flipped_pixels = set()
    for p in node.pixels:
        # relative c to c_min: new_c = (c_max - c_min) - (c - c_min) + c_min = c_max + c_min - c
        new_c = c_max + c_min - p.c
        flipped_pixels.add(Pixel(p.r, new_c, p.color))
    return GestaltNode(
        id=f"{node.id}_fliph",
        pixels=flipped_pixels,
        color=node.color,
        bbox=node.bbox
    )

def flip_node_v(node: GestaltNode) -> GestaltNode:
    """Flips the node vertically across its center."""
    r_min, c_min, r_max, c_max = node.bbox
    flipped_pixels = set()
    for p in node.pixels:
        new_r = r_max + r_min - p.r
        flipped_pixels.add(Pixel(new_r, p.c, p.color))
    return GestaltNode(
        id=f"{node.id}_flipv",
        pixels=flipped_pixels,
        color=node.color,
        bbox=node.bbox
    )

# Selection Primitives
def select_by_color(nodes: list[GestaltNode], color: int) -> list[GestaltNode]:
    return [n for n in nodes if n.color == color]

def select_by_size(nodes: list[GestaltNode], size: int) -> list[GestaltNode]:
    return [n for n in nodes if len(n.pixels) == size]

def get_largest(nodes: list[GestaltNode]) -> list[GestaltNode]:
    if not nodes:
        return []
    max_size = max(len(n.pixels) for n in nodes)
    return [n for n in nodes if len(n.pixels) == max_size]
