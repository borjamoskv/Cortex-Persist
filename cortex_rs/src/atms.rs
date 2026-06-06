use uuid::Uuid;
use std::collections::{HashMap, HashSet};
use pyo3::prelude::*;

#[pyclass]
#[derive(Debug, Clone)]
pub struct AtmsGraph {
    pub nodes: HashSet<Uuid>,
    pub dependencies: HashMap<Uuid, Vec<Uuid>>, // Child -> Parents (DependsOn)
    pub entails: HashMap<Uuid, Vec<Uuid>>,      // Parent -> Children (Entails)
    pub conflicts: HashMap<Uuid, Vec<Uuid>>,    // Node -> Conflicting nodes
}

#[pymethods]
impl AtmsGraph {
    #[new]
    pub fn new() -> Self {
        AtmsGraph {
            nodes: HashSet::new(),
            dependencies: HashMap::new(),
            entails: HashMap::new(),
            conflicts: HashMap::new(),
        }
    }

    pub fn add_node(&mut self, node_id_str: &str) -> PyResult<()> {
        let node_id = Uuid::parse_str(node_id_str)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        self.nodes.insert(node_id);
        Ok(())
    }

    pub fn add_dependency(&mut self, child_str: &str, parent_str: &str) -> PyResult<()> {
        let child = Uuid::parse_str(child_str)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        let parent = Uuid::parse_str(parent_str)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        
        self.dependencies.entry(child).or_insert_with(Vec::new).push(parent);
        self.entails.entry(parent).or_insert_with(Vec::new).push(child);
        Ok(())
    }
}
