use std::io::{BufWriter, Write};
use std::fs::OpenOptions;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};
use serde_json;

use crate::reality::claim::{ClaimStatus, VerifiableClaimInput, VerifiableClaimRecord};
use crate::reality::scorer::TrustScorer;
use crate::reality::validator::{ValidationError, Validator};

pub struct ClaimsLedger {
    ledger_path: String,
    validator: Validator,
}

impl ClaimsLedger {
    pub fn new(ledger_path: &str) -> Self {
        Self {
            ledger_path: ledger_path.to_string(),
            validator: Validator::default(),
        }
    }

    /// Punto de entrada único para ingerir un claim (Event Sourcing).
    /// El claim de entrada (DTO) se evalúa determinísticamente.
    /// Se produce un Event (Record) que se adjunta al Ledger append-only.
    pub fn ingest(
        &self,
        claim_input: VerifiableClaimInput,
        now_epoch_ms: u64,
    ) -> Result<ClaimStatus, ValidationError> {

        let multi = claim_input.sources.len() >= 2;
        let trust_score = TrustScorer::score(&claim_input.sources, multi);

        let status = match self.validator.validate(&claim_input, trust_score, now_epoch_ms) {
            Ok(()) => ClaimStatus::Accepted,
            Err(ref e) => {
                eprintln!("[LEDGER] Rejected: {e}");
                ClaimStatus::Rejected
            }
        };

        let record = VerifiableClaimRecord {
            input: claim_input,
            trust_score,
            status: status.clone(),
            frozen_at: SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() * 1000,
        };

        self.append_to_ledger(&record)?;

        Ok(status)
    }

    fn append_to_ledger(
        &self,
        record: &VerifiableClaimRecord,
    ) -> Result<(), ValidationError> {
        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(Path::new(&self.ledger_path))
            .map_err(|e| ValidationError::StorageFailure { reason: e.to_string() })?;

        let mut writer = BufWriter::new(file);
        let line = serde_json::to_string(record).map_err(|e| ValidationError::StorageFailure { reason: format!("Serialization error: {e}") })?;
        writeln!(writer, "{line}").map_err(|e| ValidationError::StorageFailure { reason: e.to_string() })?;

        Ok(())
    }
}
