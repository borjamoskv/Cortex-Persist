import logging

from .ingestion import GestaltNode, Pixel

logger = logging.getLogger("cortex.agents.arc_agi_3.dsl")

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

# AX-043: Advanced Kinetic Primitives
def detect_symmetry(node: GestaltNode) -> dict[str, bool]:
    """Detects horizontal and vertical symmetry within a node."""
    r_min, c_min, r_max, c_max = node.bbox
    pixels = {(p.r, p.c) for p in node.pixels}
    
    h_sym = True
    for r, c in pixels:
        mirror_c = c_max + c_min - c
        if (r, mirror_c) not in pixels:
            h_sym = False
            break
            
    v_sym = True
    for r, c in pixels:
        mirror_r = r_max + r_min - r
        if (mirror_r, c) not in pixels:
            v_sym = False
            break
            
    return {"horizontal": h_sym, "vertical": v_sym}

def get_centroid(node: GestaltNode) -> tuple[float, float]:
    """Calculates the center of mass of the node."""
    if not node.pixels:
        return (0.0, 0.0)
    avg_r = sum(p.r for p in node.pixels) / len(node.pixels)
    avg_c = sum(p.c for p in node.pixels) / len(node.pixels)
    return (avg_r, avg_c)

def fill_contour(node: GestaltNode, color: int) -> GestaltNode:
    """Fills the interior of a node's bounding box with a color (simple fill)."""
    r_min, c_min, r_max, c_max = node.bbox
    new_pixels = set(node.pixels)
    for r in range(r_min, r_max + 1):
        for c in range(c_min, c_max + 1):
            new_pixels.add(Pixel(r, c, color))
    return GestaltNode(
        id=f"{node.id}_filled",
        pixels=new_pixels,
        color=color,
        bbox=node.bbox
    )

def apply_gravity(nodes: list[GestaltNode], direction: str = "down", bounds: tuple[int, int] = (30, 30)) -> list[GestaltNode]:
    """Simulates gravity by shifting nodes until they hit the boundary or another node."""
    max_r, max_c = bounds
    # Sort nodes by position to process them in order (e.g., bottom-up for down gravity)
    if direction == "down":
        sorted_nodes = sorted(nodes, key=lambda n: n.bbox[2], reverse=True)
        dr, dc = 1, 0
    elif direction == "up":
        sorted_nodes = sorted(nodes, key=lambda n: n.bbox[0])
        dr, dc = -1, 0
    else:
        return nodes # Simplified

    # For now, a very simple 'stack' logic or boundary check
    # Real ARC gravity is often about falling until collision
    # This is a placeholder for the logic to be synthesized
    return sorted_nodes
