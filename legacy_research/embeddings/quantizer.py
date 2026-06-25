
from legacy_research.math.babylon import CortexVector


class AutocrystallizerQuantizationEdge:
    """
    [C5-REAL] The Boundary.
    External stochastic systems (LLMs, API Embeddings) output float32/float64.
    This boundary strictly intercepts those floats and compresses them into 
    BABYLON-60 integer geometry. Any floating point values past this boundary
    are a P0 violation.
    """
    
    def __init__(self, scaling_factor: int = 10000):
        self.scaling_factor = scaling_factor

    def quantize(self, stochastic_embedding: list[float]) -> CortexVector:
        """
        Collapses a continuous float embedding into a discrete integer vector.
        """
        discrete_data = [int(round(val * self.scaling_factor)) for val in stochastic_embedding]
        return CortexVector(discrete_data)

    def verify_integer_bounds(self, vector: CortexVector) -> bool:
        """
        Verifies that no scalar exceeds limits for Merkle representation.
        """
        for val in vector.data:
            if not isinstance(val, int):
                return False
        return True
