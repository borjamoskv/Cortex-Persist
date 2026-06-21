use cortex_ffi::BoundaryKernel;
use cortex_replay::{divergence, ReplayEngine};
use cortex_rs::CortexKernel;

#[test]
fn membrane_rejects_poisoned_ir() {
    let mut kernel = BoundaryKernel::new();
    let out = kernel.submit_ir("{\"op\":\"STORE\",\"args\":[\"\0\",\"NULL\"]}");
    assert!(out == "REJECTED" || out.starts_with("HARD_FAIL"));
}

#[test]
fn kernel_collapses_on_fork_pressure() {
    let mut kernel = CortexKernel::new();
    let out = kernel.submit_ir("FORK");
    assert!(matches!(out, cortex_types::KernelResult::Collapse { .. }));
    assert!(kernel.collapse_detected());
}

#[test]
fn replay_is_bit_identical_for_same_seed() {
    let engine = ReplayEngine { kernel_factory: CortexKernel::new };

    let a = engine.run_universe(42, 7, 10_000);
    let b = engine.run_universe(42, 7, 10_000);

    assert_eq!(a.stats, b.stats);
    assert_eq!(a.universe.ledger_root, b.universe.ledger_root);
    assert_eq!(a.universe.kernel_hash, b.universe.kernel_hash);
    assert_eq!(divergence(&a, &b), 0);
}
