use cortex_replay::{simulate_universe, calculate_divergence, SwanState, generate_event};

#[test]
fn test_deterministic_event_generation() {
    let state1 = SwanState { seed: 42, epoch: 1, entropy_index: 500 };
    let state2 = SwanState { seed: 42, epoch: 1, entropy_index: 500 };
    
    assert_eq!(generate_event(&state1), generate_event(&state2), "Must be bit-for-bit reproducible");
}

#[test]
fn test_universe_survival_reproducibility() {
    let trace_a = simulate_universe(999, "baseline");
    let trace_b = simulate_universe(999, "baseline");

    let divergence = calculate_divergence(&trace_a, &trace_b);
    assert_eq!(divergence, 0, "Identical universes must have 0 divergence");
}

#[test]
fn test_multiverse_divergence_metrics() {
    let trace_base = simulate_universe(1337, "baseline");
    let trace_weak = simulate_universe(1337, "weak_collapse_gate");

    let divergence = calculate_divergence(&trace_base, &trace_weak);
    assert!(divergence > 0, "Altered kernel policy must yield measurable divergence > 0");
}
