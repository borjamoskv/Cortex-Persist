use pyo3::prelude::*;

#[pyclass(from_py_object)]
#[derive(Debug, Clone)]
pub struct BeliefPlaneScheduler {
    pub weight_rel: f64,
    pub weight_conf: f64,
    pub weight_rec: f64,
}

#[pymethods]
impl BeliefPlaneScheduler {
    #[new]
    #[pyo3(signature = (weight_rel=1.0, weight_conf=1.0, weight_rec=1.0))]
    pub fn new(weight_rel: f64, weight_conf: f64, weight_rec: f64) -> Self {
        BeliefPlaneScheduler {
            weight_rel,
            weight_conf,
            weight_rec,
        }
    }

    /// Computes the epistemic score for a memory payload.
    /// Score(m) = Integrity * (((Rel*w_r) + (Conf*w_c) + (Rec*w_t)) / (1.0 + Cost + Risk))
    pub fn compute_memory_score(
        &self,
        rel: f64,
        conf: f64,
        rec: f64,
        cost: f64,
        risk: f64,
        integrity_multiplier: f64,
    ) -> PyResult<f64> {
        let numerator = (rel * self.weight_rel) + (conf * self.weight_conf) + (rec * self.weight_rec);
        let denominator = 1.0 + cost + risk;
        
        let integrity_cubed = integrity_multiplier * integrity_multiplier * integrity_multiplier;
        Ok(integrity_cubed * (numerator / denominator))
    }
}
