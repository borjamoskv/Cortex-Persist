import hashlib
from dataclasses import dataclass
from typing import Any, Optional

# Expected to import EpistemicState, EpistemicEvent from membrane
# from .membrane import EpistemicEvent, EpistemicState

@dataclass
class EpistemicField:
    curvature: float
    direction: list[float]
    uncertainty_density: float

def _hash_to_vector(trace: Optional[dict], dim: int = 64) -> list[float]:
    """Generates a deterministic directional vector from the solver trace."""
    if not trace:
        return [0.0] * dim
    h = hashlib.sha256(str(trace).encode()).digest()
    # Normalize between -0.5 and 0.5
    return [(b / 255.0) - 0.5 for b in h[:dim]]

def epistemic_projection(event: Any) -> EpistemicField:
    """Transforms an EpistemicEvent into an attractive tensor field."""
    k = 0.1
    state_val = event.state.value if hasattr(event.state, 'value') else str(event.state)
    
    if state_val == "unknown":
        k = 1.0
    elif state_val == "undecidable":
        k = 1.5
    elif state_val == "solver-silent":
        k = 2.0

    return EpistemicField(
        curvature=k * event.entropy_signature,
        direction=_hash_to_vector(event.z3_trace),
        uncertainty_density=1.0 - event.confidence
    )

def update_metric(g: list[list[float]], epistemic_field: EpistemicField) -> list[list[float]]:
    """Deforms the g_ij Riemannian metric based on the epistemic field."""
    dim = len(g)
    direction = epistemic_field.direction
    if len(direction) < dim:
        direction = direction + [0.0] * (dim - len(direction))
        
    for i in range(dim):
        for j in range(len(g[i])):
            g[i][j] += (
                epistemic_field.curvature *
                direction[i] *
                direction[j]
            )
    return g

def compute_geodesic(g_static: list[list[float]], g_dynamic: list[list[float]]) -> list[float]:
    """Computes the shortest path through the deformed space."""
    dim = len(g_dynamic)
    shift = [0.0] * dim
    for i in range(dim):
        shift[i] = g_dynamic[i][i] - g_static[i][i]
    return shift

def apply_mutation(ast: Any, vector: list[float], event: Optional[Any] = None) -> Any:
    """
    Applies the multi-dimensional drift vector to the AST.
    If the event indicates a logical collapse, UAO generates structure directly.
    """
    if event:
        state_val = event.state.value if hasattr(event.state, 'value') else str(event.state)
        if state_val in ["unknown", "solver-silent", "undecidable"]:
            from .ghost import ghost_manifold_engine
            from .uop import unknown_as_operator
            new_ast = unknown_as_operator(event)
            if new_ast is not None:
                # Ghost Manifold Absorbs the geometry of failure
                ghost_manifold_engine.absorb_uop_ast(new_ast)
                return new_ast
                
    return ast

def autodidact_step(ast: Any, g_static: list[list[float]], g_dynamic: list[list[float]], epistemic_events: list[Any]) -> Any:
    """
    The Autodidact Drift Operator.
    Navigates the geometry of structured ignorance instead of avoiding errors.
    """
    from .ghost import ghost_manifold_engine
    dim = len(g_dynamic)
    drift_vector = [0.0] * dim

    # 1. Apply passive background deformation from Ghost Manifold
    g_dynamic = ghost_manifold_engine.propagate(g_dynamic)

    # 2. Process active epistemic events
    for event in epistemic_events:
        field = epistemic_projection(event)
        g_dynamic = update_metric(g_dynamic, field)

        for i in range(dim):
            dir_val = field.direction[i] if i < len(field.direction) else 0.0
            drift_vector[i] += field.curvature * dir_val

    geodesic = compute_geodesic(g_static, g_dynamic)
    
    final_vector = [geodesic[i] + drift_vector[i] for i in range(dim)]
    
    # Track dominant unknown state for UAO
    dominant_event = epistemic_events[-1] if epistemic_events else None

    return apply_mutation(ast, final_vector, dominant_event)
