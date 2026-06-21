import hashlib
from dataclasses import dataclass
from typing import Any

# Expected to import RetrievalState, RetrievalEvent from membrane
# from .membrane import RetrievalEvent, RetrievalState


@dataclass
class RetrievalField:
    curvature: float
    direction: list[float]
    uncertainty_density: float


def _hash_to_vector(trace: dict | None, dim: int = 64) -> list[float]:
    """Generates a deterministic directional vector from the solver trace."""
    if not trace:
        return [0.0] * dim
    h = hashlib.sha256(str(trace).encode()).digest()
    # Normalize between -0.5 and 0.5
    return [(b / 255.0) - 0.5 for b in h[:dim]]


def retrieval_projection(event: Any) -> RetrievalField:
    """Transforms an RetrievalEvent into an attractive tensor field."""
    k = 0.1
    state_val = event.state.value if hasattr(event.state, "value") else str(event.state)

    if state_val == "unknown":
        k = 1.0
    elif state_val == "undecidable":
        k = 1.5
    elif state_val == "solver-silent":
        k = 2.0

    return RetrievalField(
        curvature=k * event.entropy_signature,
        direction=_hash_to_vector(event.z3_trace),
        uncertainty_density=1.0 - event.confidence,
    )


def update_metric(g: list[list[float]], retrieval_field: RetrievalField) -> list[list[float]]:
    """Deforms the g_ij Riemannian metric based on the retrieval field."""
    dim = len(g)
    direction = retrieval_field.direction
    if len(direction) < dim:
        direction = direction + [0.0] * (dim - len(direction))

    for i in range(dim):
        for j in range(len(g[i])):
            g[i][j] += retrieval_field.curvature * direction[i] * direction[j]
    return g


def compute_geodesic(g_static: list[list[float]], g_dynamic: list[list[float]]) -> list[float]:
    """Computes the shortest path through the deformed space."""
    dim = len(g_dynamic)
    shift = [0.0] * dim
    for i in range(dim):
        shift[i] = g_dynamic[i][i] - g_static[i][i]
    return shift


def apply_mutation(ast: Any, vector: list[float], event: Any | None = None) -> Any:
    """
    Applies the multi-dimensional drift vector to the AST.
    If the event indicates a logical collapse, UAO generates structure directly.
    """
    if event:
        state_val = event.state.value if hasattr(event.state, "value") else str(event.state)
        if state_val in ["unknown", "solver-silent", "undecidable"]:
            from .ghost import ghost_manifold_engine
            from .uop import unknown_as_operator

            new_ast = unknown_as_operator(event)
            if new_ast is not None:
                # Ghost Manifold Absorbs the geometry of failure
                ghost_manifold_engine.absorb_uop_ast(new_ast)
                return new_ast

    return ast


def autodidact_step(
    ast: Any, g_static: list[list[float]], g_dynamic: list[list[float]], retrieval_events: list[Any]
) -> Any:
    """
    The Autodidact Drift Operator.
    Navigates the geometry of structured ignorance instead of avoiding errors.
    """
    from .ghost import ghost_manifold_engine

    dim = len(g_dynamic)
    drift_vector = [0.0] * dim

    # 1. Apply passive background deformation from Ghost Manifold
    g_dynamic = ghost_manifold_engine.propagate(g_dynamic)

    # 2. Process active retrieval events
    for event in retrieval_events:
        field = retrieval_projection(event)
        g_dynamic = update_metric(g_dynamic, field)

        for i in range(dim):
            dir_val = field.direction[i] if i < len(field.direction) else 0.0
            drift_vector[i] += field.curvature * dir_val

    geodesic = compute_geodesic(g_static, g_dynamic)

    final_vector = [geodesic[i] + drift_vector[i] for i in range(dim)]

    # Track dominant unknown state for UAO
    dominant_event = retrieval_events[-1] if retrieval_events else None

    return apply_mutation(ast, final_vector, dominant_event)
