use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use crate::mee::state::Account;
use crate::mee::event::TransferEvent;
use crate::mee::ledger::{hash_state, hash_event, hash_transition};
use crate::mee::runtime::apply;
use crate::mee::proof::ProofArtifact;

#[pyfunction]
pub fn execute_mee_transfer(state_json: &str, event_json: &str) -> PyResult<String> {
    // 1. Deserialize Inputs
    let initial_state: Account = serde_json::from_str(state_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid state JSON: {e}")))?;
    
    let event: TransferEvent = serde_json::from_str(event_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid event JSON: {e}")))?;

    // 2. Hash pre-state and event
    let initial_hash = hash_state(&initial_state);
    let event_hash = hash_event(&event);

    // 3. Deterministic Runtime Transition
    let final_state = apply(&initial_state, &event);
    let final_hash = hash_state(&final_state);

    // 4. Ledger Causal Record
    let transition_hash = hash_transition(&initial_hash, &event_hash, &final_hash);

    // 5. Build Proof Artifact
    let proof = ProofArtifact {
        prev_balance: initial_state.balance,
        delta: event.delta,
        next_balance: final_state.balance,
        prev_state_hash: initial_hash,
        event_hash,
        next_state_hash: final_hash,
        transition_hash,
    };

    // Return as serialized string
    serde_json::to_string(&proof)
        .map_err(|e| PyValueError::new_err(format!("Failed to serialize proof: {e}")))
}
