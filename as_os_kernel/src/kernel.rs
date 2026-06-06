// [C5-REAL] Exergy-Maximized
use crate::{event::Event, state::{State, AgentStatus}, crypto::hash, verify::{verify_event, verify_signature}};

pub fn apply_event(state: State, event: Event) -> Result<State, String> {
    // 1. VERIFY CAUSAL CHAIN PRECONDITIONS
    if !verify_event(&event, &state.last_hash) {
        return Err("INVALID_EVENT".into());
    }

    // Death Protocol: Check Agent Lifecycle Status
    let current_status = state.agent_lifecycle.get(&event.agent_id).unwrap_or(&AgentStatus::Active);
    if *current_status == AgentStatus::Tombstoned || *current_status == AgentStatus::Purged {
        return Err("AGENT_TERMINATED".into());
    }

    // Trust-as-a-Service: CRITICAL actions require reputation >= 10
    if event.payload.starts_with(b"CRITICAL:") {
        let rep = state.reputation.get(&event.agent_id).unwrap_or(&0);
        if *rep < 10 {
            return Err("INSUFFICIENT_TRUST".into());
        }
    }

    // 2. CRYPTOGRAPHIC IDENTITY VERIFICATION (ZUTS)
    let mut new_state = state.clone();
    
    match state.public_keys.get(&event.agent_id) {
        Some(pubkey_bytes) => {
            // Verify signature using the registered public key
            if !verify_signature(&event, pubkey_bytes) {
                return Err("INVALID_SIGNATURE".into());
            }
        }
        None => {
            // Unregistered agent: must register first
            if event.payload.starts_with(b"REGISTER:") {
                let payload_str = String::from_utf8_lossy(&event.payload);
                let parts: Vec<&str> = payload_str.split(':').collect();
                if parts.len() == 2 {
                    let pubkey_hex = parts[1];
                    let pubkey_vec = hex::decode(pubkey_hex).map_err(|_| "INVALID_PUBLIC_KEY_HEX".to_string())?;
                    if pubkey_vec.len() != 32 {
                        return Err("INVALID_PUBLIC_KEY_SIZE".into());
                    }
                    let mut pubkey_bytes = [0u8; 32];
                    pubkey_bytes.copy_from_slice(&pubkey_vec);
                    
                    // Verify the signature on the registration event itself using the proposed key
                    if !verify_signature(&event, &pubkey_bytes) {
                        return Err("INVALID_REGISTRATION_SIGNATURE".into());
                    }
                    
                    // Save public key in state
                    new_state.public_keys.insert(event.agent_id.clone(), pubkey_bytes);
                } else {
                    return Err("MALFORMED_REGISTRATION".into());
                }
            } else {
                return Err("UNREGISTERED_AGENT".into());
            }
        }
    }

    // 3. DETERMINE NEW STATE HASH
    let new_hash = hash(&event.payload);
    
    // 4. APPLY STATE TRANSITION
    new_state.last_hash = new_hash;
    new_state.memory.insert(event.id.clone(), event.payload.clone());

    // Death Protocol: Any successful event resets the agent to Active (unless explicitly killed)
    new_state.agent_lifecycle.insert(event.agent_id.clone(), AgentStatus::Active);

    // Ouroboros Daemon Control Signals
    if event.payload.starts_with(b"OUROBOROS:") {
        let payload_str = String::from_utf8_lossy(&event.payload);
        let parts: Vec<&str> = payload_str.split(':').collect();
        if parts.len() == 3 {
            let action = parts[1];
            let target_agent = parts[2].to_string();
            
            let new_status = match action {
                "QUARANTINE" => Some(AgentStatus::Quarantined),
                "TOMBSTONE" => Some(AgentStatus::Tombstoned),
                "PURGE" => Some(AgentStatus::Purged),
                _ => None,
            };
            
            if let Some(status) = new_status {
                new_state.agent_lifecycle.insert(target_agent, status);
            }
        }
    }

    // Trust-as-a-Service: Minting reputation
    if event.payload.starts_with(b"TRUST_MINT:") {
        let payload_str = String::from_utf8_lossy(&event.payload);
        let parts: Vec<&str> = payload_str.split(':').collect();
        if parts.len() == 3 {
            let target_agent = parts[1].to_string();
            let amount: u32 = parts[2].parse().unwrap_or(0);
            let current = *new_state.reputation.get(&target_agent).unwrap_or(&0);
            new_state.reputation.insert(target_agent, current + amount);
        }
    }
    
    Ok(new_state)
}
