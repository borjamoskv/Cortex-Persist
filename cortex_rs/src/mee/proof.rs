use serde::{Deserialize, Serialize};

/// The precursor to the .b60 artifact.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProofArtifact {
    pub prev_balance: i64,
    pub delta: i64,
    pub next_balance: i64,
    pub prev_state_hash: String,
    pub event_hash: String,
    pub next_state_hash: String,
    pub transition_hash: String, // The final causal proof
}
