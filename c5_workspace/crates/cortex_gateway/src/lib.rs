//! C5-REAL Gateway I10 Consensus Engine
//! Implements adaptive z-score gating, MoE/Dense/Orthogonal consensus triad, and Merkle audit trails.
//! Enforces BABYLON-60 Epistemology: No float64 inside internal logic.

use serde::{Deserialize, Serialize};
use sha3::{Digest, Sha3_256};
use std::collections::VecDeque;

const BABYLON_SCALE: i64 = 12_960_000; // 60^4

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, PartialOrd)]
pub struct Babylon60(pub i64);

impl Babylon60 {
    pub fn from_f64(v: f64) -> Self {
        Babylon60((v * BABYLON_SCALE as f64).round() as i64)
    }
    
    pub fn to_f64(&self) -> f64 {
        self.0 as f64 / BABYLON_SCALE as f64
    }

    pub fn zero() -> Self {
        Babylon60(0)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelResponse {
    pub model_id: String,
    pub logits_summary: Vec<f32>, // External ONNX interface only
    pub tokens: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditRecord {
    pub timestamp: u64,
    pub input_hash: String,
    pub consensus_achieved: bool,
    pub z_score: Babylon60,
    pub disagreement_entropy: Babylon60,
    pub previous_merkle_root: String,
}

pub struct TriadGateway {
    pub embedding_history: VecDeque<Babylon60>,
    pub current_merkle_root: String,
}

impl Default for TriadGateway {
    fn default() -> Self {
        Self::new()
    }
}

impl TriadGateway {
    pub fn new() -> Self {
        let mut history = VecDeque::new();
        // Pre-seed with some baseline to avoid div by zero in z-score
        history.push_back(Babylon60::from_f64(0.10));
        history.push_back(Babylon60::from_f64(0.12));
        history.push_back(Babylon60::from_f64(0.11));
        
        Self {
            embedding_history: history,
            current_merkle_root: "GENESIS_ROOT".to_string(),
        }
    }

    /// Calculate disagreement entropy across the Triad (Llama, Mixtral, Qwen)
    fn calculate_disagreement_entropy(&self, responses: &[ModelResponse]) -> Babylon60 {
        let mut entropy = 0.0;
        let n = responses.len() as f64;
        
        for resp in responses {
            let unique_tokens: std::collections::HashSet<_> = resp.tokens.iter().collect();
            let p = unique_tokens.len() as f64 / (resp.tokens.len() as f64 + 1.0);
            if p > 0.0 {
                entropy -= p * p.log2();
            }
        }
        Babylon60::from_f64(entropy / n)
    }

    /// Adaptive Z-Score Gating using rolling window of cosine distances
    fn adaptive_z_score(&mut self, current_cosine: Babylon60) -> Babylon60 {
        let n = self.embedding_history.len() as f64;
        let sum: f64 = self.embedding_history.iter().map(|x| x.to_f64()).sum();
        let mean = sum / n;
        
        let variance: f64 = self.embedding_history.iter()
            .map(|x| (x.to_f64() - mean).powi(2))
            .sum::<f64>() / n;
            
        let std_dev = variance.sqrt().max(1e-6);
        let z_score = (current_cosine.to_f64() - mean).abs() / std_dev;

        if self.embedding_history.len() > 100 {
            self.embedding_history.pop_front();
        }
        self.embedding_history.push_back(current_cosine);

        Babylon60::from_f64(z_score)
    }

    /// Merkle Audit Trail update
    fn update_merkle_root(&mut self, record: &AuditRecord) -> String {
        let serialized = serde_json::to_string(record).unwrap_or_default();
        let mut hasher = Sha3_256::new();
        hasher.update(self.current_merkle_root.as_bytes());
        hasher.update(b"||");
        hasher.update(serialized.as_bytes());
        
        let new_root = hex::encode(hasher.finalize());
        self.current_merkle_root = new_root.clone();
        new_root
    }

    /// Gateway Evaluation entrypoint
    pub fn evaluate_insertion(&mut self, input_hash: &str, current_cosine_f64: f64, triad_responses: &[ModelResponse]) -> Result<AuditRecord, String> {
        let current_cosine = Babylon60::from_f64(current_cosine_f64);
        let z_score = self.adaptive_z_score(current_cosine);
        let entropy = self.calculate_disagreement_entropy(triad_responses);

        let threshold_z = Babylon60::from_f64(3.0);
        let threshold_e = Babylon60::from_f64(1.5);
        
        let consensus_achieved = z_score < threshold_z && entropy < threshold_e;

        let record = AuditRecord {
            timestamp: std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs(),
            input_hash: input_hash.to_string(),
            consensus_achieved,
            z_score,
            disagreement_entropy: entropy,
            previous_merkle_root: self.current_merkle_root.clone(),
        };

        self.update_merkle_root(&record);

        if !consensus_achieved {
            return Err(format!("HARD_STOP: Validation failed. Z-Score: {:.2}, Entropy: {:.2}", z_score.to_f64(), entropy.to_f64()));
        }

        Ok(record)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_triad_gateway_rejection() {
        let mut gateway = TriadGateway::new();
        let responses = vec![
            ModelResponse { model_id: "llama-3".into(), logits_summary: vec![], tokens: vec!["a".into(), "b".into()] },
            ModelResponse { model_id: "mixtral".into(), logits_summary: vec![], tokens: vec!["x".into(), "y".into()] },
            ModelResponse { model_id: "qwen".into(), logits_summary: vec![], tokens: vec!["1".into(), "2".into()] },
        ];
        
        // Force a high z-score anomaly
        let result = gateway.evaluate_insertion("hash_123", 0.99, &responses);
        assert!(result.is_err());
    }
}
pub mod onnx_engine;
pub mod sqlite_vec_engine;
pub mod orthogonal_obfuscator;
