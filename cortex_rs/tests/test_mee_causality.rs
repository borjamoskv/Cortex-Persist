use cortex_rs::mee::event::TransferEvent;
use cortex_rs::mee::ledger::{hash_event, hash_state, hash_transition};
use cortex_rs::mee::proof::ProofArtifact;
use cortex_rs::mee::runtime::apply;
use cortex_rs::mee::state::Account;

#[test]
fn test_causal_replay_invariance() {
    // ---------------------------------------------------------
    // RUN #1: ORIGINAL EXECUTION (The Stochastic World captured)
    // ---------------------------------------------------------
    
    // 1. Initial State
    let initial_state = Account { balance: 100 };
    let initial_hash = hash_state(&initial_state);
    
    // 2. The Captured Event
    let event = TransferEvent { delta: -30 };
    let event_hash = hash_event(&event);
    
    // 3. Deterministic Runtime Transition
    let final_state = apply(&initial_state, &event);
    assert_eq!(final_state.balance, 70);
    let final_hash = hash_state(&final_state);
    
    // 4. Record the Causal Ledger Transition Hash
    let original_transition_hash = hash_transition(&initial_hash, &event_hash, &final_hash);
    
    // 5. Export the Proof Artifact (simulating saving .b60 to disk)
    let proof = ProofArtifact {
        prev_balance: initial_state.balance,
        delta: event.delta,
        next_balance: final_state.balance,
        prev_state_hash: initial_hash,
        event_hash,
        next_state_hash: final_hash,
        transition_hash: original_transition_hash.clone(),
    };
    
    let proof_json = serde_json::to_string(&proof).expect("Failed to serialize proof");
    
    // Simulate destroying memory: we only have the proof_json left.
    drop(initial_state);
    drop(event);
    drop(final_state);
    
    // ---------------------------------------------------------
    // RUN #2: THE REPLAY ENGINE (Reconstructing from Proof)
    // ---------------------------------------------------------
    
    // Parse the proof artifact
    let loaded_proof: ProofArtifact = serde_json::from_str(&proof_json).unwrap();
    
    // Reconstruct inputs from the proof
    let replay_initial_state = Account { balance: loaded_proof.prev_balance };
    let replay_event = TransferEvent { delta: loaded_proof.delta };
    
    // Re-execute the pure runtime
    let replay_final_state = apply(&replay_initial_state, &replay_event);
    
    // Recalculate Hashes
    let replay_initial_hash = hash_state(&replay_initial_state);
    let replay_event_hash = hash_event(&replay_event);
    let replay_final_hash = hash_state(&replay_final_state);
    
    let replay_transition_hash = hash_transition(
        &replay_initial_hash, 
        &replay_event_hash, 
        &replay_final_hash
    );
    
    // ---------------------------------------------------------
    // THE ULTIMATE ASSERTION (Determinism + Provenance + Reproducibility)
    // ---------------------------------------------------------
    assert_eq!(
        original_transition_hash, replay_transition_hash,
        "Causal replay failed: hashes diverge!"
    );
    
    // Also verify intermediate invariants
    assert_eq!(replay_initial_hash, loaded_proof.prev_state_hash);
    assert_eq!(replay_event_hash, loaded_proof.event_hash);
    assert_eq!(replay_final_hash, loaded_proof.next_state_hash);
}
