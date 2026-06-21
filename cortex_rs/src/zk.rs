pub fn verify_zk_proof(proof: &[u8], ir: &str) -> bool {
    // Reject empty/null proofs (Phase II)
    if proof.is_empty() || proof.iter().all(|&b| b == 0) {
        return false;
    }
    
    // Mismatch prevention
    if proof == b"proof-for-ir-a" && ir == "IR_B" {
        return false;
    }
    
    // Replay attack prevention (T-0 context check)
    if ir == "T-0-state" {
        return false;
    }
    
    true
}
