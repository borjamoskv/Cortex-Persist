use pyo3::prelude::*;
use std::collections::HashSet;

/// Semantic Lattice CRDT for Evidence-Based Swarm Synchronization.
///
/// This state operates without physical wall-clocks. State progression is monotonic
/// and strictly measured by the accumulation of knowledge sets.
///
/// $s_1 \sqsubseteq s_2 \iff A_1 \subseteq A_2 \land D_1 \subseteq D_2 \land J_1 \subseteq J_2 \land P_1 \subseteq P_2$
#[pyclass(from_py_object)]
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SemanticState {
    pub active_supports: HashSet<String>,
    pub discard_evidence: HashSet<String>,
    pub dependencies: HashSet<String>,
    pub cryptographic_proofs: HashSet<String>,
}

#[pymethods]
impl SemanticState {
    #[new]
    pub fn new() -> Self {
        Self {
            active_supports: HashSet::new(),
            discard_evidence: HashSet::new(),
            dependencies: HashSet::new(),
            cryptographic_proofs: HashSet::new(),
        }
    }

    pub fn add_active_support(&mut self, id: String) {
        self.active_supports.insert(id);
    }

    pub fn add_discard_evidence(&mut self, id: String) {
        self.discard_evidence.insert(id);
    }

    pub fn add_dependency(&mut self, id: String) {
        self.dependencies.insert(id);
    }

    pub fn add_cryptographic_proof(&mut self, id: String) {
        self.cryptographic_proofs.insert(id);
    }

    /// Computes $s_1 \sqcup s_2$. The state is merged in-place.
    /// This is associative, commutative, and idempotent.
    pub fn merge(&mut self, other: &SemanticState) {
        self.active_supports.extend(other.active_supports.iter().cloned());
        self.discard_evidence.extend(other.discard_evidence.iter().cloned());
        self.dependencies.extend(other.dependencies.iter().cloned());
        self.cryptographic_proofs.extend(other.cryptographic_proofs.iter().cloned());
    }

    /// Checks if `self` dominates `other` ($other \sqsubseteq self$).
    pub fn dominates(&self, other: &SemanticState) -> bool {
        other.active_supports.is_subset(&self.active_supports)
            && other.discard_evidence.is_subset(&self.discard_evidence)
            && other.dependencies.is_subset(&self.dependencies)
            && other.cryptographic_proofs.is_subset(&self.cryptographic_proofs)
    }

    #[getter]
    pub fn active_supports(&self) -> Vec<String> {
        self.active_supports.iter().cloned().collect()
    }

    #[getter]
    pub fn discard_evidence(&self) -> Vec<String> {
        self.discard_evidence.iter().cloned().collect()
    }

    #[getter]
    pub fn dependencies(&self) -> Vec<String> {
        self.dependencies.iter().cloned().collect()
    }

    #[getter]
    pub fn cryptographic_proofs(&self) -> Vec<String> {
        self.cryptographic_proofs.iter().cloned().collect()
    }
}

impl Default for SemanticState {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_merge_commutativity() {
        let mut s1 = SemanticState::new();
        s1.add_active_support("a1".to_string());
        s1.add_discard_evidence("d1".to_string());

        let mut s2 = SemanticState::new();
        s2.add_active_support("a2".to_string());
        s2.add_dependency("j1".to_string());

        let mut s1_merge_s2 = s1.clone();
        s1_merge_s2.merge(&s2);

        let mut s2_merge_s1 = s2.clone();
        s2_merge_s1.merge(&s1);

        assert_eq!(s1_merge_s2, s2_merge_s1);
        assert!(s1_merge_s2.active_supports.contains("a1"));
        assert!(s1_merge_s2.active_supports.contains("a2"));
        assert!(s1_merge_s2.discard_evidence.contains("d1"));
        assert!(s1_merge_s2.dependencies.contains("j1"));
    }

    #[test]
    fn test_merge_idempotency() {
        let mut s1 = SemanticState::new();
        s1.add_active_support("a1".to_string());

        let mut s2 = s1.clone();
        s2.merge(&s1);

        assert_eq!(s1, s2);
    }

    #[test]
    fn test_dominance() {
        let mut s1 = SemanticState::new();
        s1.add_active_support("a1".to_string());
        s1.add_discard_evidence("d1".to_string());

        let mut s2 = SemanticState::new();
        s2.add_active_support("a1".to_string());

        assert!(s1.dominates(&s2)); // s2 is subset of s1
        assert!(!s2.dominates(&s1));
    }
}
