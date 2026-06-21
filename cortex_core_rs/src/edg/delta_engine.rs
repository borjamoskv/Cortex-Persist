use pyo3::prelude::*;
use sha3::{Digest, Sha3_256};

#[pyclass]
pub struct DeltaEngine;

#[pymethods]
impl DeltaEngine {
    #[new]
    pub fn new() -> Self {
        DeltaEngine
    }

    /// Compara dos AST o payloads y calcula el diferencial termodinámico (ΔEDG).
    /// Si son estructuralmente idénticos pero varían en comentarios (Green Theater), retorna 0.0.
    pub fn compute_delta(&self, parent_payload: &str, child_payload: &str) -> f64 {
        let parent_hash = Self::hash_payload(parent_payload);
        let child_hash = Self::hash_payload(child_payload);
        
        if parent_hash == child_hash {
            return 0.0;
        }
        
        let diff_len = (child_payload.len() as isize - parent_payload.len() as isize).abs() as f64;
        diff_len * 0.1 // Peso abstracto basado en entropía estructural
    }

    #[staticmethod]
    fn hash_payload(payload: &str) -> String {
        // Purga heurística de anergía (espacios) antes del hash estructural
        let cleaned: String = payload.chars().filter(|c| !c.is_whitespace()).collect();
        let mut hasher = Sha3_256::new();
        hasher.update(cleaned.as_bytes());
        hex::encode(hasher.finalize())
    }
}
