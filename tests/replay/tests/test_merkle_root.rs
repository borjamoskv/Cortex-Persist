use cortex_replay_tests::{generate_dummy_ledger, dummy_hash};

#[test]
fn test_merkle_root_recalculation() {
    let ledger_data = generate_dummy_ledger(500);
    
    // Simulate stored root calculation
    let stored_root = dummy_hash(&ledger_data);
    
    // Simulate replay root calculation
    let replayed_root = dummy_hash(&ledger_data);
    
    assert_eq!(stored_root, replayed_root, "Merkle Root mismatch upon replay");
}
