use pyo3::prelude::*;
use petgraph::graph::{DiGraph, NodeIndex};
use std::collections::HashMap;

#[pyclass]
pub struct EDGReconstructor {
    graph: DiGraph<String, f64>,
    node_map: HashMap<String, NodeIndex>,
}

#[pymethods]
impl EDGReconstructor {
    #[new]
    pub fn new() -> Self {
        EDGReconstructor {
            graph: DiGraph::new(),
            node_map: HashMap::new(),
        }
    }

    /// Añade un nodo epistémico al EDG. Retorna el índice interno.
    pub fn add_epistemic_node(&mut self, commit_hash: String) -> usize {
        if let Some(&idx) = self.node_map.get(&commit_hash) {
            return idx.index();
        }
        let idx = self.graph.add_node(commit_hash.clone());
        self.node_map.insert(commit_hash, idx);
        idx.index()
    }

    /// Añade una transición causal (Edge) con un peso basado en la exergía calculada (Δ).
    pub fn add_causal_transition(&mut self, parent_hash: String, child_hash: String, delta_weight: f64) {
        let parent_idx = self.add_epistemic_node(parent_hash);
        let child_idx = self.add_epistemic_node(child_hash);
        
        self.graph.add_edge(NodeIndex::new(parent_idx), NodeIndex::new(child_idx), delta_weight);
    }
    
    /// Evalúa si el nodo es huérfano (invalidez epistémica tras un purge).
    pub fn is_orphan(&self, commit_hash: String) -> bool {
        if let Some(&idx) = self.node_map.get(&commit_hash) {
            // Un nodo es huérfano si no tiene edges entrantes, salvo que sea el root.
            // Para la simulación, consideramos esto.
            let incoming = self.graph.edges_directed(idx, petgraph::Direction::Incoming).count();
            return incoming == 0 && self.graph.node_count() > 1; 
        }
        true
    }
    
    pub fn node_count(&self) -> usize {
        self.graph.node_count()
    }
}
