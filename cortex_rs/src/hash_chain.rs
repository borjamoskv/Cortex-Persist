// [C5-REAL] Exergy-Maximized
// B-8: Merkle Tree Batch Computation

use crate::event_schema::{Hash, LedgerEvent};
use serde::{Deserialize, Serialize};
use sha2::Sha256;
use sha3::{Digest, Sha3_256};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MerkleRoot {
    pub root_hash: String,
    pub batch_id: String,
    pub leaves: Vec<String>,
}

pub fn compute_merkle_root(batch_id: &str, event_hashes: &[String]) -> MerkleRoot {
    if event_hashes.is_empty() {
        return MerkleRoot {
            root_hash: String::from("genesis"),
            batch_id: batch_id.to_string(),
            leaves: vec![],
        };
    }

    let mut current_level = event_hashes.to_vec();

    while current_level.len() > 1 {
        let mut next_level = Vec::new();
        for chunk in current_level.chunks(2) {
            let left = &chunk[0];
            let right = if chunk.len() > 1 { &chunk[1] } else { left };
            
            let mut hasher = Sha3_256::new();
            hasher.update(left.as_bytes());
            hasher.update(right.as_bytes());
            next_level.push(hex::encode(hasher.finalize()));
        }
        current_level = next_level;
    }

    MerkleRoot {
        root_hash: current_level[0].clone(),
        batch_id: batch_id.to_string(),
        leaves: event_hashes.to_vec(),
    }
}



/// Computes the cryptographic SHA-256 hash of a LedgerEvent.
/// The `hash` field itself is cleared during serialization to ensure
/// a deterministic pre-image.
pub fn compute_event_hash(event: &LedgerEvent) -> Result<Hash, serde_json::Error> {
    let mut canonical = event.clone();
    canonical.hash = String::new();

    // serde_json::to_value followed by serialization of that Value
    // guarantees sorted keys because Value's Map is a BTreeMap.
    let value = serde_json::to_value(&canonical)?;
    let canonical_json = serde_json::to_string(&value)?;

    let mut hasher = Sha256::new();
    hasher.update(canonical_json.as_bytes());
    let digest = hasher.finalize();
    Ok(format!("{:x}", digest))
}

/// Verifies that the event is cryptographically valid and correctly linked
/// to the previous event in the chain.
pub fn verify_event(
    event: &LedgerEvent,
    previous: Option<&LedgerEvent>,
) -> Result<bool, serde_json::Error> {
    // 1. Verify hash linkage
    match previous {
        Some(prev) => {
            if event.previous_hash.as_ref() != Some(&prev.hash) {
                return Ok(false);
            }
        }
        None => {
            if event.previous_hash.is_some() {
                return Ok(false);
            }
        }
    }

    // 2. Verify own hash matches content digest
    let expected = compute_event_hash(event)?;
    Ok(event.hash == expected)
}

/// Manages a series of cryptographically chained LedgerEvents.
#[derive(Debug, Clone, Default)]
pub struct HashChain {
    pub events: Vec<LedgerEvent>,
}

impl HashChain {
    pub fn new() -> Self {
        Self::default()
    }

    /// Appends an event to the chain, generating its previous_hash and final hash.
    pub fn append_event(&mut self, mut event: LedgerEvent) -> Result<Hash, serde_json::Error> {
        let prev_hash = self.events.last().map(|e| e.hash.clone());
        event.previous_hash = prev_hash;

        let hash = compute_event_hash(&event)?;
        event.hash = hash.clone();

        self.events.push(event);
        Ok(hash)
    }

    /// Verifies the cryptographic integrity of the entire chain.
    pub fn verify_chain(&self) -> Result<bool, serde_json::Error> {
        for i in 0..self.events.len() {
            let prev = if i > 0 {
                Some(&self.events[i - 1])
            } else {
                None
            };
            if !verify_event(&self.events[i], prev)? {
                return Ok(false);
            }
        }
        Ok(true)
    }
}
