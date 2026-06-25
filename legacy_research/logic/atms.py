# [C5-REAL] Exergy-Maximized
import logging

class AtmsAdapter:
    """
    Python implementation of the Assumption Truth Maintenance System.
    Provides local DAG tracking and cycle detection to prevent Causal loops.
    Replaces deprecated cortex_rs.AtmsGraph.
    """

    def __init__(self):
        self._nodes = set()
        self._dependencies = {}  # child -> set of parents
        self._children = {}      # parent -> set of children

    def add_node(self, node_id: str) -> None:
        """Add a causal or logical node to the ATMS graph."""
        self._nodes.add(str(node_id))

    def add_dependency(self, child_id: str, parent_id: str) -> None:
        """Define a causal dependency between two facts."""
        child_id = str(child_id)
        parent_id = str(parent_id)
        
        self.add_node(child_id)
        self.add_node(parent_id)
        
        # Cycle detection: if child is an ancestor of parent, adding this creates a cycle
        if self._is_ancestor(child_id, parent_id):
            raise ValueError(f"Causal cycle detected: {parent_id} cannot depend on {child_id}")
            
        if child_id not in self._dependencies:
            self._dependencies[child_id] = set()
        self._dependencies[child_id].add(parent_id)
        
        if parent_id not in self._children:
            self._children[parent_id] = set()
        self._children[parent_id].add(child_id)

    def _is_ancestor(self, possible_ancestor: str, node: str) -> bool:
        """Check if possible_ancestor is a direct or indirect parent of node."""
        if node not in self._dependencies:
            return False
        if possible_ancestor in self._dependencies[node]:
            return True
        for parent in self._dependencies[node]:
            if self._is_ancestor(possible_ancestor, parent):
                return True
        return False

    @property
    def nodes(self) -> set:
        return set(self._nodes)

