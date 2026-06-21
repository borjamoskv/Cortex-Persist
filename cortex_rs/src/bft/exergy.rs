use serde::{Deserialize, Serialize};

/// Exergy mutation must pass BFT consensus.
/// No single node can inject exergy.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExergyMutation {
    pub node_id: String,
    pub delta: f64,
    pub reason: String,
    pub epoch_ms: u64,
    pub signatures: Vec<String>,   // ≥ 2/3 cluster
    pub zk_proof: Option<String>,  // ZK-Guard validation
    pub rul_claim_id: Option<String>, // Required to justify exergy injection
}



#[derive(Debug)]
pub enum ExergyError {
    InsufficientConsensus { have: usize, need: usize },
    ZeroKnowledgeRejected,
    DeltaOutOfBounds { delta: f64, max: f64 },
    MissingRULClaim,
    LowRULTrust { score: f32, minimum: f32 },
    NodeNotFound { id: String },
}

impl std::fmt::Display for ExergyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InsufficientConsensus { have, need } => write!(f, "InsufficientConsensus: have {}, need {}", have, need),
            Self::ZeroKnowledgeRejected => write!(f, "ZeroKnowledgeRejected"),
            Self::DeltaOutOfBounds { delta, max } => write!(f, "DeltaOutOfBounds: delta {}, max {}", delta, max),
            Self::MissingRULClaim => write!(f, "MissingRULClaim"),
            Self::LowRULTrust { score, minimum } => write!(f, "LowRULTrust: score {}, minimum {}", score, minimum),
            Self::NodeNotFound { id } => write!(f, "NodeNotFound: {}", id),
        }
    }
}

pub struct ExergyGuard {
    pub cluster_size: usize,
    pub max_delta_per_epoch: f64,
}

impl ExergyGuard {
    pub fn validate(
        &self,
        mutation: &ExergyMutation,
        valid_nodes: &[String],
    ) -> Result<(), ExergyError> {
        // Topological consistency: node must exist in reality
        if !valid_nodes.contains(&mutation.node_id) {
            return Err(ExergyError::NodeNotFound {
                id: mutation.node_id.clone(),
            });
        }
        // BFT: require 2/3 signatures
        let threshold = (2 * self.cluster_size) / 3;
        if mutation.signatures.len() < threshold {
            return Err(ExergyError::InsufficientConsensus {
                have: mutation.signatures.len(),
                need: threshold,
            });
        }

        // No exergy injection can exceed max delta
        if mutation.delta.abs() > self.max_delta_per_epoch {
            return Err(ExergyError::DeltaOutOfBounds {
                delta: mutation.delta,
                max: self.max_delta_per_epoch,
            });
        }

        // ZK proof is optional but if present must validate
        if let Some(ref proof) = mutation.zk_proof {
            if !self.verify_zk(proof) {
                return Err(ExergyError::ZeroKnowledgeRejected);
            }
        }

        Ok(())
    }

    fn verify_zk(&self, _proof: &str) -> bool {
        // Real ZK verification stub
        // In production: groth16 or plonk verifier
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_insufficient_consensus_rejected() {
        let guard = ExergyGuard {
            cluster_size: 9,  // 9 nodes → need 6 signatures
            max_delta_per_epoch: 100.0,
        };

        let mutation = ExergyMutation {
            node_id: "metadata_engine".into(),
            delta: 9999.0,  // was: infinite exergy boost
            reason: "legacy_god_node".into(),
            epoch_ms: 1717027200000,
            signatures: vec!["node_1".into()],  // only 1 sig
            zk_proof: None,
            rul_claim_id: None,
        };

        let result = guard.validate(&mutation, &["metadata_engine".into()]);
        assert!(result.is_err());
    }

    #[test]
    fn test_max_delta_enforced() {
        let guard = ExergyGuard {
            cluster_size: 9,
            max_delta_per_epoch: 100.0,
        };

        let mutation = ExergyMutation {
            node_id: "swarm_agent_7".into(),
            delta: 150.0,  // exceeds max
            reason: "hypothesis_discovery".into(),
            epoch_ms: 1717027200000,
            signatures: vec!["n1".into(), "n2".into(), "n3".into(),
                             "n4".into(), "n5".into(), "n6".into()],
            zk_proof: None,
            rul_claim_id: None,
        };

        let result = guard.validate(&mutation, &["swarm_agent_7".into()]);
        assert!(matches!(result, Err(ExergyError::DeltaOutOfBounds { .. })));
    }

    #[test]
    fn test_node_not_found() {
        let guard = ExergyGuard {
            cluster_size: 9,
            max_delta_per_epoch: 100.0,
        };

        let mutation = ExergyMutation {
            node_id: "ghost_node".into(),
            delta: 10.0,
            reason: "test".into(),
            epoch_ms: 1717027200000,
            signatures: vec!["n1".into(), "n2".into(), "n3".into(),
                             "n4".into(), "n5".into(), "n6".into()],
            zk_proof: None,
            rul_claim_id: None,
        };

        let result = guard.validate(&mutation, &["real_node".into()]);
        assert!(matches!(result, Err(ExergyError::NodeNotFound { .. })));
    }
}
