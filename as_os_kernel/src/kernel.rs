use crate::{event::Event, state::State, crypto::hash, verify::verify_event};

pub fn apply_event(state: State, event: Event) -> Result<State, String> {
    // 1. VERIFY PRECONDITIONS
    if !verify_event(&event, &state.last_hash) {
        return Err("INVALID_EVENT".into());
    }
    // 2. DETERMINE NEW STATE HASH
    let new_hash = hash(&event.payload);
    
    // 3. APPLY STATE TRANSITION
    let mut new_state = state.clone();
    new_state.last_hash = new_hash;
    new_state.memory.insert(event.id.clone(), event.payload.clone());
    
    Ok(new_state)
}
