# [C5-REAL] Exergy-Maximized
"""
Informational Entropy and Semantic Collapse.
Implements Zlib Normalized Compression Distance (NCD) as a proxy for Shannon Entropy / KL Divergence.
"""
import zlib
import zlib
import time
from typing import Optional, Dict, Any

MAX_KINETIC_MULTIPLIER = 2.0

def kolmogorov_approx(content: str) -> float:
    """
    Approximates Kolmogorov complexity using zlib compression.
    Returns the length of the compressed bytes.
    """
    if not content:
        return 0.0
    encoded = content.encode("utf-8")
    compressed = zlib.compress(encoded, level=9)
    return float(len(compressed))

def compute_ncd(content_a: str, content_b: str) -> float:
    """
    Normalized Compression Distance (NCD) between two strings.
    NCD(x,y) = (Z(x + y) - min(Z(x), Z(y))) / max(Z(x), Z(y))
    Approaches 0 for identical strings, 1 for orthogonal strings.
    """
    if not content_a and not content_b:
        return 0.0
        
    z_a = kolmogorov_approx(content_a)
    z_b = kolmogorov_approx(content_b)
    
    # We add a small separator to avoid accidental boundary compression,
    # though technically z_ab = z(a + b)
    z_ab = kolmogorov_approx(content_a + " " + content_b)
    
    if max(z_a, z_b) == 0.0:
        return 0.0
        
    # NCD calculation
    # Due to zlib overhead, z_ab can sometimes be slightly higher than z_a + z_b,
    # or min(z_a, z_b) might be very small. We cap it to [0, 1] for safety.
    ncd = (z_ab - min(z_a, z_b)) / max(z_a, z_b)
    return max(0.0, min(ncd, 1.0))

def collapse_eligible(content_a: str, content_b: str, mass_a: float, mass_b: float, threshold: float = 0.05, mass_tolerance: float = 0.1) -> bool:
    """
    Determines if two nodes should be collapsed based on semantic redundancy and kinetic equivalence.
    """
    ncd = compute_ncd(content_a, content_b)
    mass_delta = abs(mass_a - mass_b)
    return (ncd < threshold) and (mass_delta < mass_tolerance)

def semantic_collapse(id_a: str, content_a: str, mass_a: float, 
                      id_b: str, content_b: str, mass_b: float, now: Optional[float] = None) -> Dict[str, Any]:
    """
    Executes a physical semantic collapse.
    Strict Merge Strategy (Survival of the Fittest):
    Inherits the content of the node with the highest kinetic mass.
    """
    t = now or time.time()
    
    # Determine the winner
    if mass_a >= mass_b:
        winner_id, winner_content, winner_mass = id_a, content_a, mass_a
        loser_id = id_b
    else:
        winner_id, winner_content, winner_mass = id_b, content_b, mass_b
        loser_id = id_a
        
    # Recalculate properties
    merged_content = winner_content
    # Mass inherits the strongest, capped at MAX_KINETIC_MULTIPLIER
    final_mass = min(winner_mass, MAX_KINETIC_MULTIPLIER)
    
    return {
        "id": f"{id_a}_{id_b}_collapsed",
        "content": merged_content,
        "kinetic_mass": final_mass,
        "entropy_approx": kolmogorov_approx(merged_content),
        "collapsed_from": [id_a, id_b],
        "winner": winner_id,
        "collapse_timestamp": t,
        "irreconcilable": False
    }
