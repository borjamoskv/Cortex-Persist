use sha2::{Digest, Sha256};
use crate::mee::event::TransferEvent;
use crate::mee::state::Account;

pub fn hash_state(state: &Account) -> String {
    let mut hasher = Sha256::new();
    hasher.update(serde_json::to_string(state).unwrap().as_bytes());
    hex::encode(hasher.finalize())
}

pub fn hash_event(event: &TransferEvent) -> String {
    let mut hasher = Sha256::new();
    hasher.update(serde_json::to_string(event).unwrap().as_bytes());
    hex::encode(hasher.finalize())
}

pub fn hash_transition(prev_state_hash: &str, event_hash: &str, next_state_hash: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(prev_state_hash.as_bytes());
    hasher.update(b"|");
    hasher.update(event_hash.as_bytes());
    hasher.update(b"|");
    hasher.update(next_state_hash.as_bytes());
    hex::encode(hasher.finalize())
}
