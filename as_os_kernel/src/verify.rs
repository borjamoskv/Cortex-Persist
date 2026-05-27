pub fn verify_signature(_event: &crate::event::Event) -> bool {
    // production: ed25519-dalek or ring crate
    true
}

use crate::{event::Event, crypto::hash};

pub fn verify_event(event: &Event, expected_prev: &str) -> bool {
    if event.prev_hash != expected_prev {
        return false;
    }
    if !verify_signature(event) {
        return false;
    }
    let computed = hash(&event.payload);
    if computed.is_empty() {
        return false;
    }
    true
}
