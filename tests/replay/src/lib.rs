// Placeholder for internal replay utilities.
// Tests are located in the tests/ directory.
use sha2::{Sha256, Digest};

pub fn dummy_hash(data: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(data);
    let result = hasher.finalize();
    let mut hash = [0u8; 32];
    hash.copy_from_slice(&result);
    hash
}

pub fn generate_dummy_ledger(events: usize) -> Vec<u8> {
    let mut ledger = Vec::new();
    for i in 0..events {
        let event_data = format!("Event_{}", i);
        ledger.extend_from_slice(event_data.as_bytes());
        ledger.push(b'\n'); // delimiter
    }
    ledger
}
