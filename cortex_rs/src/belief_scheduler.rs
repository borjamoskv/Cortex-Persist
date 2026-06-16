use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

/// Belief Plane Memory Scheduler
/// Implements the multivariable tensor equation for context injection scoring
/// according to the CORTEX-NATIVE-ARCHITECTURE Doctrine.
#[pyclass(from_py_object)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryScheduler {
    #[pyo3(get, set)]
    pub weight_rel: f32,  // Relevance weight
    #[pyo3(get, set)]
    pub weight_conf: f32, // Confidence weight
    #[pyo3(get, set)]
    pub weight_rec: f32,  // Recency weight
}

#[pymethods]
impl MemoryScheduler {
    #[new]
    #[pyo3(signature = (weight_rel=1.0, weight_conf=1.0, weight_rec=1.0))]
    pub fn new(weight_rel: f32, weight_conf: f32, weight_rec: f32) -> Self {
        MemoryScheduler {
            weight_rel,
            weight_conf,
            weight_rec,
        }
    }

    /// Computes the injection score for a memory candidate.
    /// Score(m) = ((Rel * w_r) + (Conf * w_c) + (Rec * w_t)) / (Cost_tokens + Risk_contam)
    /// If Risk_contam detects cascading structural contradictions (>= 0.9), score asymptotes to 0.
    #[pyo3(signature = (relevance, confidence, recency, cost_tokens, risk_contam))]
    pub fn compute_injection_score(
        &self,
        relevance: f32,
        confidence: f32,
        recency: f32,
        cost_tokens: f32,
        risk_contam: f32,
    ) -> f32 {
        if risk_contam >= 0.9 {
            // Structural contradiction detected. Hard zero.
            return 0.0;
        }

        let numerator = (relevance * self.weight_rel)
            + (confidence * self.weight_conf)
            + (recency * self.weight_rec);
        
        // Prevent division by zero or negative costs
        let safe_cost = if cost_tokens <= 0.0 { 1.0 } else { cost_tokens };
        let denominator = safe_cost + risk_contam;
        
        numerator / denominator
    }
}
