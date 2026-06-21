
use crate::reality::claim::{ClaimStatus, RealityClaim};
use crate::reality::scorer::TrustScorer;
use crate::reality::validator::{ValidationError, Validator};
use crate::reality::writer::RealityWriter;

pub struct RealityRegistry {
    writer: RealityWriter,
    validator: Validator,
}

impl RealityRegistry {
    pub fn new(ledger_path: &str) -> Self {
        Self {
            writer: RealityWriter::new(ledger_path),
            validator: Validator::default(),
        }
    }

    pub fn ingest(
        &self,
        mut claim: RealityClaim,
        now_epoch_ms: u64,
    ) -> Result<ClaimStatus, ValidationError> {

        let multi = claim.sources.len() >= 2;
        claim.trust_score = TrustScorer::score(&claim.sources, multi);

        let status = match self.validator.validate(&claim, now_epoch_ms) {
            Ok(()) => ClaimStatus::Verified,
            Err(ref e) => {
                eprintln!("[LKRGSER] Rejected: {e}");
                ClaimStatus::Rejected
            }
        };
        claim.status = status.clone();

        let line = serde_json::to_string(&claim).map_err(|e| ValidationError::StorageFailure { reason: format!("Serialization error: {e}") })?;
        self.writer.write_claim(&line).map_err(|e| ValidationError::StorageFailure { reason: format!("WAL flush error: {e}") })?;

        Ok(status)
    }
}
