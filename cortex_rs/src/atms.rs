use std::collections::{HashMap, HashSet, VecDeque};
use pyo3::prelude::*;
use crate::belief_object::BeliefState;

pub type BeliefId = String;

#[pyclass(from_py_object)]
#[derive(Debug, Clone)]
pub struct BeliefNode {
    #[pyo3(get, set)]
    pub id: BeliefId,

    /// Dependencias que justifican esta creencia.
    #[pyo3(get, set)]
    pub supports: Vec<BeliefId>,

    /// Creencias que dependen de esta.
    #[pyo3(get, set)]
    pub dependents: Vec<BeliefId>,

    #[pyo3(get, set)]
    pub state: BeliefState,

    /// Epoch de invalidación.
    #[pyo3(get, set)]
    pub epoch: u64,
}

#[pyclass(from_py_object)]
#[derive(Debug, Clone)]
pub struct AtmsGraph {
    pub nodes: HashMap<BeliefId, BeliefNode>,
    pub current_epoch: u64,
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
        Self {
            nodes: HashMap::new(),
            current_epoch: 0,
        }
    }

    pub fn belief_count(&self) -> usize {
        self.nodes.len()
    }

    pub fn add_belief(&mut self, id: &str) -> PyResult<()> {
        let id_str = id.to_string();
        self.nodes.entry(id_str.clone()).or_insert(BeliefNode {
            id: id_str,
            supports: Vec::new(),
            dependents: Vec::new(),
            state: BeliefState::Active,
            epoch: self.current_epoch,
        });
        Ok(())
    }

    pub fn add_dependency(&mut self, support: &str, dependent: &str) -> PyResult<()> {
        self.add_belief(support)?;
        self.add_belief(dependent)?;

        let support_str = support.to_string();
        let dependent_str = dependent.to_string();

        if let Some(support_node) = self.nodes.get_mut(&support_str) {
            if !support_node.dependents.contains(&dependent_str) {
                support_node.dependents.push(dependent_str.clone());
            }
        }

        if let Some(dependent_node) = self.nodes.get_mut(&dependent_str) {
            if !dependent_node.supports.contains(&support_str) {
                dependent_node.supports.push(support_str);
            }
        }
        Ok(())
    }

    pub fn get_state(&self, id: &str) -> PyResult<Option<BeliefState>> {
        Ok(self.nodes.get(id).map(|n| n.state))
    }

    pub fn is_active(&self, id: &str) -> PyResult<bool> {
        Ok(matches!(
            self.nodes.get(id).map(|n| n.state),
            Some(BeliefState::Active)
        ))
    }

    pub fn refute(&mut self, root: &str) -> PyResult<Vec<BeliefId>> {
        self.current_epoch = self.current_epoch.wrapping_add(1);
        let epoch = self.current_epoch;
        let mut affected = Vec::new();
        let mut queue = VecDeque::new();
        let mut visited = HashSet::new();
        
        let root_str = root.to_string();

        let root_node = match self.nodes.get_mut(&root_str) {
            Some(node) => node,
            None => return Ok(affected),
        };

        root_node.state = BeliefState::Discarded;
        root_node.epoch = epoch;

        queue.push_back(root_str.clone());
        visited.insert(root_str.clone());
        affected.push(root_str.clone());

        while let Some(current) = queue.pop_front() {
            let dependents = self
                .nodes
                .get(&current)
                .map(|n| n.dependents.clone())
                .unwrap_or_default();

            for child_id in dependents {
                if !visited.insert(child_id.clone()) {
                    continue;
                }

                let child_supports = self
                    .nodes
                    .get(&child_id)
                    .map(|n| n.supports.clone())
                    .unwrap_or_default();

                let all_supports_dead = child_supports.iter().all(|sid| {
                    self.nodes
                        .get(sid)
                        .map(|n| n.state != BeliefState::Active)
                        .unwrap_or(true)
                });

                if let Some(child) = self.nodes.get_mut(&child_id) {
                    child.epoch = epoch;
                    child.state = if all_supports_dead {
                        BeliefState::Orphaned
                    } else {
                        BeliefState::Discarded
                    };
                }

                queue.push_back(child_id.clone());
                affected.push(child_id.clone());
            }
        }

        Ok(affected)
    }

    pub fn reactivate(&mut self, belief_id: &str) -> PyResult<bool> {
        match self.nodes.get_mut(belief_id) {
            Some(node) => {
                node.state = BeliefState::Active;
                Ok(true)
            }
            None => Ok(false),
        }
    }

    pub fn epoch(&self) -> u64 {
        self.current_epoch
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn simple_chain_refutation() {
        let mut atms = AtmsGraph::new();

        atms.add_dependency("1", "2").unwrap();
        atms.add_dependency("2", "3").unwrap();
        atms.add_dependency("3", "4").unwrap();

        let affected = atms.refute("1").unwrap();

        assert_eq!(affected.len(), 4);

        assert_eq!(
            atms.get_state("1").unwrap(),
            Some(BeliefState::Discarded)
        );

        assert!(matches!(
            atms.get_state("2").unwrap(),
            Some(BeliefState::Discarded) | Some(BeliefState::Orphaned)
        ));

        assert!(matches!(
            atms.get_state("3").unwrap(),
            Some(BeliefState::Discarded) | Some(BeliefState::Orphaned)
        ));

        assert!(matches!(
            atms.get_state("4").unwrap(),
            Some(BeliefState::Discarded) | Some(BeliefState::Orphaned)
        ));
    }

    #[test]
    fn diamond_dependency_graph() {
        let mut atms = AtmsGraph::new();

        atms.add_dependency("1", "3").unwrap();
        atms.add_dependency("2", "3").unwrap();
        atms.add_dependency("3", "4").unwrap();

        atms.refute("1").unwrap();

        assert_eq!(
            atms.get_state("1").unwrap(),
            Some(BeliefState::Discarded)
        );

        // 3 sigue teniendo soporte desde 2.
        assert!(matches!(
            atms.get_state("3").unwrap(),
            Some(BeliefState::Discarded) | Some(BeliefState::Active)
        ));
    }

    #[test]
    fn epoch_increases() {
        let mut atms = AtmsGraph::new();

        atms.add_belief("1").unwrap();

        let before = atms.epoch();

        atms.refute("1").unwrap();

        let after = atms.epoch();

        assert!(after > before);
    }
}
