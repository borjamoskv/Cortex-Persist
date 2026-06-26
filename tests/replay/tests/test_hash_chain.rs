use cortex_replay_tests::{generate_dummy_ledger, dummy_hash};

#[test]
fn test_sequential_hash_chain() {
    let ledger_data = generate_dummy_ledger(10);
    
    // Simulate chain evaluation: hash(N) = SHA256(event(N) || hash(N-1))
    let mut prev_hash = [0u8; 32];
    
    for (i, event) in ledger_data.split(|&b| b == b'\n').filter(|e| !e.is_empty()).enumerate() {
        let mut combined = Vec::new();
        combined.extend_from_slice(event);
        combined.extend_from_slice(&prev_hash);
        
        let current_hash = dummy_hash(&combined);
        
        // Assert cryptographic linkage is deterministic
        assert_ne!(prev_hash, current_hash, "Hash collision or failure at event {}", i);
        prev_hash = current_hash;
    }
}
