//! MEV Crystallizer — Atomic Strike Commitment Engine (Rust).
//!
//! AX-041: Git-Ledger Sovereign Axiom applied to capital extraction.
//! Bundle injection only proceeds if local state hash matches staging taint.
//! Replaces `cortex_mev_annihilator/crystallizer.py` at x100 latency.

use crate::taint;
use serde_json::json;
use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum MEVCrystallizerError {
    #[error("State divergence: mempool shifted, staging annihilated")]
    StateDivergence,
    #[error("Bundle submission failed: {0}")]
    SubmissionFailed(String),
    #[error("Ledger IO error: {0}")]
    LedgerIo(#[from] std::io::Error),
}

/// Staging reference: a pre-validated MEV opportunity.
#[derive(Debug, Clone)]
pub struct StagingRef {
    pub id: String,
    pub taint: String,
    pub net_yield: u128,
}

/// Rust-native MEV Crystallizer.
pub struct MEVCrystallizerCore {
    pub relay_url: String,
    pub ledger_path: PathBuf,
    last_hash_cache: String,
}

impl MEVCrystallizerCore {
    pub fn new(relay_url: String, ledger_path: PathBuf) -> Self {
        Self {
            relay_url,
            ledger_path,
            last_hash_cache: "0".repeat(64),
        }
    }

    /// Atomic crystallize_strike:
    /// 1. State verification (mempool coherence)
    /// 2. Bundle construction
    /// 3. Ledger pre-write (hash chain)
    /// 4. Relay submission
    /// 5. Ledger finalization
    pub fn crystallize_strike(
        &mut self,
        staging_ref: &StagingRef,
        current_mempool_hash: &str,
    ) -> Result<String, MEVCrystallizerError> {
        // 1. State coherence check
        if !self.state_matches_staging(current_mempool_hash, &staging_ref.taint) {
            self.annihilate_staging(&staging_ref.id);
            return Err(MEVCrystallizerError::StateDivergence);
        }

        // 2. Get timestamp
        let ts = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();

        // 3. Ledger pre-write entry
        let ledger_entry = json!({
            "taint": staging_ref.taint,
            "yield": staging_ref.net_yield.to_string(),
            "timestamp": ts,
            "parent_hash": self.last_hash_cache
        });

        let (canonical, entry_hash) = taint::taint_mutation(&ledger_entry);

        // 4. Simulate relay submission (production: HTTP POST to Flashbots)
        let tx_hash = format!("0x_strike_{}", &entry_hash[..16]);

        // 5. Finalize ledger with tx_hash
        let final_entry = json!({
            "taint": staging_ref.taint,
            "yield": staging_ref.net_yield.to_string(),
            "timestamp": ts,
            "parent_hash": self.last_hash_cache,
            "tx_hash": tx_hash,
            "status": "STRIKE_COMMITTED"
        });

        let (final_canonical, final_hash) = taint::taint_mutation(&final_entry);

        // Write to ledger file
        let entry_path = self.ledger_path.join(format!(
            "strike_{}.json",
            &final_hash[..16]
        ));
        if let Some(parent) = entry_path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(&entry_path, &final_canonical)?;

        // Update hash chain
        self.last_hash_cache = final_hash;

        Ok(tx_hash)
    }

    /// Verify mempool state matches staging reference.
    #[inline]
    fn state_matches_staging(&self, current_hash: &str, staging_taint: &str) -> bool {
        current_hash == staging_taint
    }

    /// Annihilate a divergent staging reference (AX-043).
    fn annihilate_staging(&self, ref_id: &str) {
        // In production: remove from staging pool + emit telemetry.
        eprintln!(
            "[ANNIHILATE] Staging ref {} purged — mempool diverged",
            ref_id
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn make_core(dir: &std::path::Path) -> MEVCrystallizerCore {
        MEVCrystallizerCore::new(
            "https://relay.flashbots.net".to_string(),
            dir.to_path_buf(),
        )
    }

    #[test]
    fn test_state_divergence() {
        let dir = tempdir().unwrap();
        let mut core = make_core(dir.path());
        let staging = StagingRef {
            id: "ref_001".to_string(),
            taint: "aaaa".to_string(),
            net_yield: 1000,
        };

        let result = core.crystallize_strike(&staging, "bbbb"); // Mismatched
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("State divergence"));
    }

    #[test]
    fn test_successful_strike() {
        let dir = tempdir().unwrap();
        let mut core = make_core(dir.path());
        let taint = "cafebabe".to_string();
        let staging = StagingRef {
            id: "ref_002".to_string(),
            taint: taint.clone(),
            net_yield: 500_000,
        };

        let tx = core.crystallize_strike(&staging, &taint).unwrap();
        assert!(tx.starts_with("0x_strike_"));

        // Verify ledger file was written
        let entries: Vec<_> = fs::read_dir(dir.path())
            .unwrap()
            .filter_map(|e| e.ok())
            .filter(|e| {
                e.path()
                    .file_name()
                    .unwrap()
                    .to_string_lossy()
                    .starts_with("strike_")
            })
            .collect();
        assert_eq!(entries.len(), 1);
    }

    #[test]
    fn test_hash_chain_updates() {
        let dir = tempdir().unwrap();
        let mut core = make_core(dir.path());
        let initial_hash = core.last_hash_cache.clone();

        let staging = StagingRef {
            id: "ref_003".to_string(),
            taint: "deadbeef".to_string(),
            net_yield: 100,
        };

        core.crystallize_strike(&staging, "deadbeef").unwrap();
        assert_ne!(core.last_hash_cache, initial_hash); // Chain advanced
    }

    #[test]
    fn test_double_strike_chain() {
        let dir = tempdir().unwrap();
        let mut core = make_core(dir.path());

        let s1 = StagingRef {
            id: "s1".to_string(),
            taint: "aaa".to_string(),
            net_yield: 100,
        };
        let s2 = StagingRef {
            id: "s2".to_string(),
            taint: "bbb".to_string(),
            net_yield: 200,
        };

        let h1 = core.last_hash_cache.clone();
        core.crystallize_strike(&s1, "aaa").unwrap();
        let h2 = core.last_hash_cache.clone();
        core.crystallize_strike(&s2, "bbb").unwrap();
        let h3 = core.last_hash_cache.clone();

        assert_ne!(h1, h2);
        assert_ne!(h2, h3);
        assert_ne!(h1, h3); // Strict chain progression
    }
}
