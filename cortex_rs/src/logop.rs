use pyo3::prelude::*;
use crate::se_crdt::SemanticState;

/// Logical Opinion (LogOP) Consensus Layer Outcome.
#[pyclass(from_py_object)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BeliefOutcome {
    Accepted,
    Rejected,
    Contested,
    Orphaned,
    Unknown,
}

#[pyclass(from_py_object)]
#[derive(Debug, Clone)]
pub struct LogOpEngine;

#[pymethods]
impl LogOpEngine {
    #[new]
    pub fn new() -> Self {
        LogOpEngine
    }

    /// Resolves the logical consensus outcome of a converged SemanticState.
    ///
    /// - Discard evidence present & Active supports present => Contested
    /// - Discard evidence present & No Active supports => Rejected
    /// - Active supports present & No Discard evidence => Accepted
    /// - No active supports/discard but dependencies exist => Orphaned
    /// - Otherwise => Unknown
    pub fn resolve_outcome(&self, state: &SemanticState) -> BeliefOutcome {
        let has_discard = state.evidence.discard_evidence_len > 0 || state.provenance.compacted_discard_evidence > 0;
        let has_active = state.evidence.active_supports_len > 0 || state.provenance.compacted_active_supports > 0;
        let has_deps = state.evidence.dependencies_len > 0 || state.provenance.compacted_dependencies > 0;

        if has_discard {
            if has_active {
                BeliefOutcome::Contested
            } else {
                BeliefOutcome::Rejected
            }
        } else if has_active {
            BeliefOutcome::Accepted
        } else if has_deps {
            BeliefOutcome::Orphaned
        } else {
            BeliefOutcome::Unknown
        }
    }
}

impl Default for LogOpEngine {
    fn default() -> Self {
        Self::new()
    }
}
