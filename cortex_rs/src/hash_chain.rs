use crate::event_schema::{LedgerEvent, Hash};
use sha2::{Sha256, Digest};

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
pub fn verify_event(event: &LedgerEvent, previous: Option<&LedgerEvent>) -> Result<bool, serde_json::Error> {
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
            let prev = if i > 0 { Some(&self.events[i - 1]) } else { None };
            if !verify_event(&self.events[i], prev)? {
                return Ok(false);
            }
        }
        Ok(true)
    }
}
