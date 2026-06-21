use pyo3::prelude::*;
use sha2::{Digest, Sha256};
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct RewriteSeed {
    pub seed_hash: String,
    pub timestamp: i64,
    pub target_repo: String,
    pub operation_type: String,
}

#[pyclass]
pub struct AuditTrail {
    pub log: Vec<RewriteSeed>,
}

#[pymethods]
impl AuditTrail {
    #[new]
    pub fn new() -> Self {
        AuditTrail { log: Vec::new() }
    }

    pub fn generate_deterministic_seed(&mut self, repo_path: &str, timestamp: i64) -> String {
        let payload = format!("CORTEX_REWRITE:{}:{}", repo_path, timestamp);
        let mut hasher = Sha256::new();
        hasher.update(payload.as_bytes());
        let hash_result = hasher.finalize();
        let seed_hash = hex::encode(hash_result);

        let seed = RewriteSeed {
            seed_hash: seed_hash.clone(),
            timestamp,
            target_repo: repo_path.to_string(),
            operation_type: "MERKLE_REWRITE".to_string(),
        };

        self.log.push(seed);
        seed_hash
    }

    pub fn export_log(&self) -> String {
        serde_json::to_string(&self.log).unwrap_or_else(|_| "[]".to_string())
    }
}
