// [C5-REAL] Exergy-Maximized
use crate::event::Event;
use ed25519_dalek::{VerifyingKey, Signature, Verifier};

pub fn verify_signature(event: &Event, public_key_bytes: &[u8; 32]) -> bool {
    let verifying_key = match VerifyingKey::from_bytes(public_key_bytes) {
        Ok(vk) => vk,
        Err(_) => return false,
    };
    let signature = match Signature::from_slice(&event.signature) {
        Ok(sig) => sig,
        Err(_) => return false,
    };
    
    // Bind signature to prev_hash to prevent replay attacks
    let mut message = Vec::new();
    message.extend_from_slice(event.prev_hash.as_bytes());
    message.extend_from_slice(&event.payload);
    
    verifying_key.verify(&message, &signature).is_ok()
}

pub fn verify_event(event: &Event, expected_prev: &str) -> bool {
    if event.prev_hash != expected_prev {
        return false;
    }
    true
}
