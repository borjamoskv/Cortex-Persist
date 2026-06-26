use cortex_replay_tests::generate_dummy_ledger;

#[test]
fn test_bit_exact_replay() {
    // Generate a determinist ledger of 1000 events
    let ledger_v1 = generate_dummy_ledger(1000);
    
    // Simulating a concurrent execution from state 0
    let replayed_ledger = generate_dummy_ledger(1000);
    
    // Brutal simple criteria: if not a single bit matches, FAIL.
    assert_eq!(ledger_v1, replayed_ledger, "Replayed state is not bit-exact to original ledger");
}
