use cortex_replay_tests::generate_dummy_ledger;

#[test]
fn test_replay_equivalence_classes() {
    let branch_a = generate_dummy_ledger(100);
    let branch_b = generate_dummy_ledger(100);
    
    // Since our dummy ledger generator is fully deterministic, branch A and B must be equal
    assert_eq!(branch_a, branch_b, "Equivalence class violation: deterministic executions diverged");
}
