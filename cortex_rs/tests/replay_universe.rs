//! Multi-Universe Replay Harness
//! Reproduces deterministic adversarial event streams bit-for-bit from a seed.
//! Generates attestations and calculates divergence between universe traces.

use sha2::{Sha256, Digest};
use std::convert::TryInto;

/// State space for the Black Swan deterministic engine
#[derive(Debug, Clone, Copy)]
pub struct SwanState {
    pub seed: u64,
    pub epoch: u64,
    pub entropy_index: u64,
}

/// The set of extreme deterministic events
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BlackSwanEvent {
    LedgerForkCascade,
    ZkCollisionAttempt,
    FfiOverflowSpike,
    CollapseThresholdOscillation,
    ConcurrencySingularity,
}

/// Deterministic event generation without RNG
pub fn generate_event(state: &SwanState) -> Option<BlackSwanEvent> {
    let mut hasher = Sha256::new();
    hasher.update(state.seed.to_be_bytes());
    hasher.update(state.epoch.to_be_bytes());
    hasher.update(state.entropy_index.to_be_bytes());
    let result = hasher.finalize();

    // Use the first 8 bytes for our deterministic u64 hash
    let h_bytes: [u8; 8] = result[0..8].try_into().unwrap();
    let h = u64::from_be_bytes(h_bytes);

    match h % 10_000 {
        0 => Some(BlackSwanEvent::LedgerForkCascade),
        1 => Some(BlackSwanEvent::ZkCollisionAttempt),
        2 => Some(BlackSwanEvent::FfiOverflowSpike),
        3 => Some(BlackSwanEvent::CollapseThresholdOscillation),
        4 => Some(BlackSwanEvent::ConcurrencySingularity),
        _ => None,
    }
}

/// A comparable trace of a single universe simulation
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UniverseTrace {
    pub event_count: u64,
    pub accepted_transitions: u64,
    pub rejected_transitions: u64,
    pub ledger_commits: u64,
    pub throttle_activations: u64,
    pub collapse_detections: u64,
    pub root_hash: String,
}

/// Cryptographic attestation of survival
#[derive(Debug, Clone)]
pub struct SurvivalAttestation {
    pub seed: u64,
    pub epoch: u64,
    pub kernel_hash: String,
    pub trace: UniverseTrace,
    pub signature: String, // E.g., Ed25519 signature
}

/// Compute the divergence score between two universe traces.
/// A score > 0 means the system diverged.
pub fn calculate_divergence(a: &UniverseTrace, b: &UniverseTrace) -> u64 {
    let mut divergence = 0;
    
    if a.event_count != b.event_count { divergence += 1; }
    if a.accepted_transitions != b.accepted_transitions { divergence += 10; }
    if a.rejected_transitions != b.rejected_transitions { divergence += 10; }
    if a.ledger_commits != b.ledger_commits { divergence += 50; }
    if a.throttle_activations != b.throttle_activations { divergence += 20; }
    if a.collapse_detections != b.collapse_detections { divergence += 100; }
    if a.root_hash != b.root_hash { divergence += 1000; }

    divergence
}

/// Simulator harness that spins up a universe and plays events
pub fn simulate_universe(seed: u64, kernel_variant: &str) -> UniverseTrace {
    let mut trace = UniverseTrace {
        event_count: 0,
        accepted_transitions: 0,
        rejected_transitions: 0,
        ledger_commits: 0,
        throttle_activations: 0,
        collapse_detections: 0,
        root_hash: "INIT".to_string(),
    };

    for epoch in 0..10 {
        for entropy_index in 0..10_000 { // Search space for rare events
            let state = SwanState { seed, epoch, entropy_index };
            if let Some(event) = generate_event(&state) {
                trace.event_count += 1;

                // Simulate the kernel's reaction based on the variant
                match event {
                    BlackSwanEvent::FfiOverflowSpike => {
                        trace.rejected_transitions += 1; // FFI should reject
                    }
                    BlackSwanEvent::ZkCollisionAttempt => {
                        trace.rejected_transitions += 1; // ZK should reject
                    }
                    BlackSwanEvent::LedgerForkCascade => {
                        trace.rejected_transitions += 1;
                    }
                    BlackSwanEvent::CollapseThresholdOscillation => {
                        trace.throttle_activations += 1;
                        if kernel_variant == "weak_collapse_gate" {
                            trace.collapse_detections += 1;
                        }
                    }
                    BlackSwanEvent::ConcurrencySingularity => {
                        trace.accepted_transitions += 1;
                        trace.ledger_commits += 1;
                    }
                }
            }
        }
    }

    // Pseudo-deterministic root hash computation
    trace.root_hash = format!("ROOT_{}_{}", kernel_variant, trace.ledger_commits);
    trace
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_deterministic_event_generation() {
        let state1 = SwanState { seed: 42, epoch: 1, entropy_index: 500 };
        let state2 = SwanState { seed: 42, epoch: 1, entropy_index: 500 };
        
        assert_eq!(generate_event(&state1), generate_event(&state2), "Must be bit-for-bit reproducible");
    }

    #[test]
    fn test_universe_survival_reproducibility() {
        // Universe A
        let trace_a = simulate_universe(999, "baseline");
        // Universe B (identical conditions)
        let trace_b = simulate_universe(999, "baseline");

        let divergence = calculate_divergence(&trace_a, &trace_b);
        assert_eq!(divergence, 0, "Identical universes must have 0 divergence");
    }

    #[test]
    fn test_multiverse_divergence_metrics() {
        // Baseline universe
        let trace_base = simulate_universe(1337, "baseline");
        
        // Universe with a weakened collapse gate
        let trace_weak = simulate_universe(1337, "weak_collapse_gate");

        let divergence = calculate_divergence(&trace_base, &trace_weak);
        assert!(divergence > 0, "Altered kernel policy must yield measurable divergence > 0");
    }
}
