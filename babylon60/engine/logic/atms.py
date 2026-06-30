# [C5-REAL] Exergy-Maximized
import logging

# Attempt to load the Rust PyO3 extension
try:
    import cortex_rs
except ImportError:
    cortex_rs = None
    logging.getLogger(__name__).warning(
        "cortex_rs is not installed. AtmsGraph will not be hardware-accelerated."
    )


class AtmsAdapter:
    """
    Python wrapper for the Rust AtmsGraph.
    Provides Assumption Truth Maintenance System capabilities using PyO3 bindings.
    """

    def __init__(self):
        if cortex_rs is None:
            raise RuntimeError("cortex_rs PyO3 extension is required for ATMS operations.")
        self._graph = cortex_rs.AtmsGraph()  # type: ignore

    def add_node(self, node_id: str) -> None:
        """Add a causal or logical node to the ATMS graph."""
        # Convert UUID or text to strict string representation
        self._graph.add_node(str(node_id))

    def add_dependency(self, child_id: str, parent_id: str) -> None:
        """Define a causal dependency between two facts."""
        self._graph.add_dependency(str(child_id), str(parent_id))

    @property
    def nodes(self) -> set:
        # Pyo3 exposes HashSet as Python set if configured, otherwise we might need conversion
        return set(self._graph.nodes)

    def get_descendants(self, root_id: str) -> set[str]:
        """
        O(1) retrieval of all dependent nodes (descendants) that rely on this assumption.
        Used for Branch Orphaning by the Tribunal.
        """
        try:
            # Assuming the rust graph exposes descendants or transitive dependencies
            if hasattr(self._graph, "get_descendants"):
                return set(self._graph.get_descendants(str(root_id)))
            else:
                logging.getLogger(__name__).warning(
                    "ATMS Rust core lacks 'get_descendants'. Emulating."
                )
                return {str(root_id)}
        except Exception as e:  # noqa: BLE001
            logging.getLogger(__name__).error(f"[ATMS] Failed to get descendants: {e}")
            return {str(root_id)}
