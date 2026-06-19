use dashmap::DashMap;
use pyo3::prelude::*;
use std::collections::HashSet;
use std::sync::Arc;

#[pyclass]
#[derive(Clone, Debug, PartialEq)]
pub enum EpistemicStatus {
    Accepted,
    Challenged,
    Deprecated,
    Invalid,
}

#[pyclass]
#[derive(Clone)]
pub struct EpistemicNode {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get, set)]
    pub status: EpistemicStatus,
    #[pyo3(get, set)]
    pub confidence: f64,
    // dependencies: Nodes this node supports
    pub supported_by: HashSet<String>,
    // supports: Nodes that support this node
    pub supports: HashSet<String>,
}

#[pymethods]
impl EpistemicNode {
    #[new]
    pub fn new(id: String, confidence: f64) -> Self {
        EpistemicNode {
            id,
            status: EpistemicStatus::Accepted,
            confidence,
            supported_by: HashSet::new(),
            supports: HashSet::new(),
        }
    }

    #[getter]
    pub fn get_supported_by(&self) -> Vec<String> {
        self.supported_by.iter().cloned().collect()
    }

    #[getter]
    pub fn get_supports(&self) -> Vec<String> {
        self.supports.iter().cloned().collect()
    }
}

#[pyclass]
pub struct EpistemicGraph {
    nodes: Arc<DashMap<String, EpistemicNode>>,
}

#[pymethods]
impl EpistemicGraph {
    #[new]
    pub fn new() -> Self {
        EpistemicGraph {
            nodes: Arc::new(DashMap::new()),
        }
    }

    pub fn add_node(&self, node: EpistemicNode) {
        self.nodes.insert(node.id.clone(), node);
    }

    pub fn get_node_status(&self, node_id: &str) -> Option<EpistemicStatus> {
        self.nodes.get(node_id).map(|n| n.status.clone())
    }

    pub fn add_dependency(&self, supporter_id: &str, supported_id: &str) -> PyResult<()> {
        // Supporter supports Supported
        if let Some(mut supporter) = self.nodes.get_mut(supporter_id) {
            supporter.supports.insert(supported_id.to_string());
        } else {
            return Err(pyo3::exceptions::PyKeyError::new_err(format!("Node not found: {}", supporter_id)));
        }

        if let Some(mut supported) = self.nodes.get_mut(supported_id) {
            supported.supported_by.insert(supporter_id.to_string());
        } else {
            return Err(pyo3::exceptions::PyKeyError::new_err(format!("Node not found: {}", supported_id)));
        }

        Ok(())
    }

    pub fn invalidate_node(&self, node_id: &str) -> Vec<String> {
        let mut affected = Vec::new();
        let mut stack = vec![node_id.to_string()];

        while let Some(current_id) = stack.pop() {
            if let Some(mut node) = self.nodes.get_mut(&current_id) {
                if node.status != EpistemicStatus::Invalid {
                    node.status = EpistemicStatus::Invalid;
                    node.confidence = 0.0;
                    affected.push(current_id.clone());
                    
                    // Propagate invalidation to all nodes that this node supports
                    for supported_id in &node.supports {
                        stack.push(supported_id.clone());
                    }
                }
            }
        }
        
        affected
    }
}
