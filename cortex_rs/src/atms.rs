use std::collections::{HashMap, HashSet};
use pyo3::prelude::*;

#[pyclass(from_py_object)]
#[derive(Debug, Clone)]
pub struct AtmsGraph {
    pub nodes: HashSet<String>,
    pub dependencies: HashMap<String, Vec<String>>, // Child -> Parents (DependsOn)
    pub entails: HashMap<String, Vec<String>>,      // Parent -> Children (Entails)
    pub conflicts: HashMap<String, Vec<String>>,    // Node -> Conflicting nodes
}

impl Default for AtmsGraph {
    fn default() -> Self {
        Self::new()
    }
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
        self.nodes.insert(node_id_str.to_string());
        Ok(())
    }

    pub fn add_dependency(&mut self, child_str: &str, parent_str: &str) -> PyResult<()> {
        let child = child_str.to_string();
        let parent = parent_str.to_string();

        self.dependencies.entry(child.clone()).or_default().push(parent.clone());
        self.entails.entry(parent).or_default().push(child);
        Ok(())
    }
}
