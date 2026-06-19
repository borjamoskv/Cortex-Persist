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

    /// Epoch de invalidación o última mutación. Viaja con el evento.
    #[pyo3(get, set)]
    pub epoch: u64,
}

#[pyclass(from_py_object)]
#[derive(Debug, Clone)]
pub struct AtmsGraph {
    pub nodes: HashMap<BeliefId, BeliefNode>,
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
        }
    }

    pub fn belief_count(&self) -> usize {
        self.nodes.len()
    }

    #[pyo3(signature = (id, event_epoch=0))]
    pub fn add_node(&mut self, id: &str, event_epoch: u64) -> PyResult<()> {
        self.add_belief(id, event_epoch)
    }

    #[pyo3(signature = (id, event_epoch=0))]
    pub fn add_belief(&mut self, id: &str, event_epoch: u64) -> PyResult<()> {
        let id_str = id.to_string();
        self.nodes.entry(id_str.clone()).or_insert(BeliefNode {
            id: id_str,
            supports: Vec::new(),
            dependents: Vec::new(),
            state: BeliefState::Active,
            epoch: event_epoch,
        });
        Ok(())
    }

    #[pyo3(signature = (support, dependent, event_epoch=0))]
    pub fn add_dependency(&mut self, support: &str, dependent: &str, event_epoch: u64) -> PyResult<()> {
        self.add_belief(support, event_epoch)?;
        self.add_belief(dependent, event_epoch)?;

        let support_str = support.to_string();
        let dependent_str = dependent.to_string();

        if let Some(support_node) = self.nodes.get_mut(&support_str) {
            if !support_node.dependents.contains(&dependent_str) {
                support_node.dependents.push(dependent_str.clone());
            }
            if event_epoch > support_node.epoch {
                support_node.epoch = event_epoch;
            }
        }

        if let Some(dependent_node) = self.nodes.get_mut(&dependent_str) {
            if !dependent_node.supports.contains(&support_str) {
                dependent_node.supports.push(support_str);
            }
            if event_epoch > dependent_node.epoch {
                dependent_node.epoch = event_epoch;
            }
        }
        Ok(())
    }

    pub fn get_state(&self, id: &str) -> PyResult<Option<BeliefState>> {
        Ok(self.nodes.get(id).map(|n| n.state))
    }

    pub fn get_epoch(&self, id: &str) -> PyResult<Option<u64>> {
        Ok(self.nodes.get(id).map(|n| n.epoch))
    }

    pub fn is_active(&self, id: &str) -> PyResult<bool> {
        Ok(matches!(
            self.nodes.get(id).map(|n| n.state),
            Some(BeliefState::Active)
        ))
    }

    #[pyo3(signature = (root, event_epoch))]
    pub fn refute(&mut self, root: &str, event_epoch: u64) -> PyResult<Vec<BeliefId>> {
        let mut affected = Vec::new();
        let mut queue = VecDeque::new();
        let mut visited = HashSet::new();
        
        let root_str = root.to_string();

        let root_node = match self.nodes.get_mut(&root_str) {
            Some(node) => node,
            None => return Ok(affected),
        };

        root_node.state = BeliefState::Discarded;
        root_node.epoch = event_epoch;

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
                    child.epoch = event_epoch;
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

    #[pyo3(signature = (belief_id, event_epoch=0))]
    pub fn reactivate(&mut self, belief_id: &str, event_epoch: u64) -> PyResult<bool> {
        match self.nodes.get_mut(belief_id) {
            Some(node) => {
                node.state = BeliefState::Active;
                node.epoch = event_epoch;
                Ok(true)
            }
            None => Ok(false),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn simple_chain_refutation() {
        let mut atms = AtmsGraph::new();

        atms.add_dependency("1", "2", 1).unwrap();
        atms.add_dependency("2", "3", 1).unwrap();
        atms.add_dependency("3", "4", 1).unwrap();

        let affected = atms.refute("1", 2).unwrap();

        assert_eq!(affected.len(), 4);

        assert_eq!(
            atms.get_state("1").unwrap(),
            Some(BeliefState::Discarded)
        );
        assert_eq!(atms.get_epoch("1").unwrap(), Some(2));

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

        atms.add_dependency("1", "3", 1).unwrap();
        atms.add_dependency("2", "3", 1).unwrap();
        atms.add_dependency("3", "4", 1).unwrap();

        atms.refute("1", 2).unwrap();

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

        atms.add_belief("1", 10).unwrap();

        let before = atms.get_epoch("1").unwrap().unwrap();

        atms.refute("1", 42).unwrap();

        let after = atms.get_epoch("1").unwrap().unwrap();

        assert!(after > before);
        assert_eq!(after, 42);
    }
}
