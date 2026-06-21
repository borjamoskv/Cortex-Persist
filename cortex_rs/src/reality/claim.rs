use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum ClaimDomain {
    Llm,
    Api,
    System,
    Performance,
    Pricing,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum ClaimStatus {
    Accepted,
    Rejected,
    Unverified,
    Auditable,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Source {
    pub url: String,
    pub fetch_hash: String,         // SHA256 of content at fetch time
    pub fetched_at_epoch_ms: u64,
}

/// DTO (Input) - Immutable fields provided by the caller
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifiableClaimInput {
    pub claim_id: String,           // UUID v4
    pub statement: String,
    pub domain: ClaimDomain,
    pub created_at_epoch_ms: u64,
    pub sources: Vec<Source>,
    pub evidence_hashes: Vec<String>,
}

impl VerifiableClaimInput {
    pub fn is_sourceless(&self) -> bool {
        self.sources.is_empty()
    }
}

/// Event (Output) - Append-only record with validation metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifiableClaimRecord {
    pub input: VerifiableClaimInput,
    pub trust_score: f32,
    pub status: ClaimStatus,
    pub frozen_at: u64,
}
