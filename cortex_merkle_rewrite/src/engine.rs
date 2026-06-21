use pyo3::prelude::*;
use crate::heuristics::SecretHeuristics;

#[pyclass]
pub struct RewriteEngine {
    pub target_repo: String,
}

#[pymethods]
impl RewriteEngine {
    #[new]
    pub fn new(target_repo: String) -> Self {
        RewriteEngine { target_repo }
    }

    /// Evaluates if a blob or string contains sensitive information.
    pub fn evaluate_payload(&self, payload: &str) -> bool {
        SecretHeuristics::is_secret(payload)
    }

    /// Redacts secrets from the payload.
    pub fn redact_payload(&self, payload: &str) -> String {
        SecretHeuristics::redact(payload)
    }

    /// Validates the identity invariants before a rewrite operation.
    pub fn validate_invariants(&self, is_clean: bool, no_rebases: bool) -> bool {
        // Enforce the pre-flight invariants logic
        if !is_clean || !no_rebases {
            return false;
        }
        true
    }
}
