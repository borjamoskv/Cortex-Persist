use cortex_replay_tests::{generate_dummy_ledger, dummy_hash};
use rand::Rng;

#[test]
#[should_panic(expected = "Corruption detected")]
fn test_corruption_detection() {
    let mut ledger_data = generate_dummy_ledger(500);
    let original_root = dummy_hash(&ledger_data);
    
    // Induce a single bit flip / byte mutation
    let mut rng = rand::thread_rng();
    let idx = rng.gen_range(0..ledger_data.len());
    ledger_data[idx] ^= 1; // flip bit
    
    let corrupted_root = dummy_hash(&ledger_data);
    
    if original_root != corrupted_root {
        panic!("Corruption detected: replayed root does not match stored root");
    }
}
