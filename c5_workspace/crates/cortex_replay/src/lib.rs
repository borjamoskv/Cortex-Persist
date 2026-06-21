use sha2::{Sha256, Digest};
use std::convert::TryInto;

#[derive(Debug, Clone, Copy)]
pub struct SwanState {
    pub seed: u64,
    pub epoch: u64,
    pub entropy_index: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BlackSwanEvent {
    LedgerForkCascade,
    ZkCollisionAttempt,
    FfiOverflowSpike,
    CollapseThresholdOscillation,
    ConcurrencySingularity,
}

pub fn generate_event(state: &SwanState) -> Option<BlackSwanEvent> {
    let mut hasher = Sha256::new();
    hasher.update(state.seed.to_be_bytes());
    hasher.update(state.epoch.to_be_bytes());
    hasher.update(state.entropy_index.to_be_bytes());
    let result = hasher.finalize();

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

pub fn calculate_divergence(a: &UniverseTrace, b: &UniverseTrace) -> u64 {
    let mut div = 0;
    if a.event_count != b.event_count { div += 1; }
    if a.accepted_transitions != b.accepted_transitions { div += 10; }
    if a.rejected_transitions != b.rejected_transitions { div += 10; }
    if a.ledger_commits != b.ledger_commits { div += 50; }
    if a.throttle_activations != b.throttle_activations { div += 20; }
    if a.collapse_detections != b.collapse_detections { div += 100; }
    if a.root_hash != b.root_hash { div += 1000; }
    div
}

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
        for entropy_index in 0..10_000 {
            let state = SwanState { seed, epoch, entropy_index };
            if let Some(event) = generate_event(&state) {
                trace.event_count += 1;
                match event {
                    BlackSwanEvent::FfiOverflowSpike => trace.rejected_transitions += 1,
                    BlackSwanEvent::ZkCollisionAttempt => trace.rejected_transitions += 1,
                    BlackSwanEvent::LedgerForkCascade => trace.rejected_transitions += 1,
                    BlackSwanEvent::CollapseThresholdOscillation => {
                        trace.throttle_activations += 1;
                        if kernel_variant == "weak_collapse_gate" { trace.collapse_detections += 1; }
                    }
                    BlackSwanEvent::ConcurrencySingularity => {
                        trace.accepted_transitions += 1;
                        trace.ledger_commits += 1;
                    }
                }
            }
        }
    }
    trace.root_hash = format!("ROOT_{}_{}", kernel_variant, trace.ledger_commits);
    trace
}
