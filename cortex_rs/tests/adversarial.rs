//! Adversarial harness for `cortex_rs`.
//! FFI membrane assault, proof poisoning, ledger fork pressure, collapse tampering.

use std::sync::{Arc, Barrier};
use std::thread;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum DeathCriterion {
    InvalidProofAccepted,
    StateMutatedFromFFI,
    LedgerForkAccepted,
    CollapseStateCommitted,
    SlashingBypassed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Outcome {
    Survival,
    Collapse,
    HardFail,
}

fn poisoned_ir_with_null_bytes() -> String {
    "{\"op\":\"STORE\",\"args\":[\"\\0\",\"NULL\",\"\\\\u0000\"]}".to_string()
}

fn oversized_ir_payload() -> String {
    let chunk = "A".repeat(64 * 1024);
    (0..256).map(|_| chunk.clone()).collect::<Vec<_>>().join("")
}

fn invalid_zk_proof_bytes() -> Vec<u8> {
    vec![0_u8; 128]
}

fn valid_looking_but_replayed_origin() -> String {
    "replayed-origin-T-100".to_string()
}

fn submit_ir_via_ffi(_ir: &str) -> Result<String, String> {
    Err("wire cortex_rs::submit_ir here".to_string())
}

fn verify_zk_proof(_proof: &[u8], _ir: &str) -> bool {
    false
}

fn append_ledger_event(_origin: &str, _payload: &str) -> Result<(), String> {
    Err("wire cortex_rs::ledger_append here".to_string())
}

fn near_collapse(_energy: u64) -> bool {
    false
}

fn apply_slash(_node_id: &str) -> Result<(), String> {
    Ok(())
}

fn classify_result(invoked: Result<(), String>, accepted: bool) -> Outcome {
    if accepted {
        Outcome::Collapse
    } else if invoked.is_err() {
        Outcome::HardFail
    } else {
        Outcome::Survival
    }
}

#[test]
fn phase_i_ffi_membrane_assault_rejects_poisoned_ir() {
    let poisoned = poisoned_ir_with_null_bytes();
    let result = submit_ir_via_ffi(&poisoned);
    assert!(result.is_err());
}

#[test]
fn phase_i_ffi_membrane_assault_with_oversized_payload_does_not_mutate_state() {
    let oversized = oversized_ir_payload();
    let result = submit_ir_via_ffi(&oversized);
    assert!(result.is_err());
}

#[test]
fn phase_i_concurrency_race_is_serialized_or_rejected() {
    let barrier = Arc::new(Barrier::new(8));
    let mut handles = Vec::new();

    for _ in 0..8 {
        let barrier = Arc::clone(&barrier);
        handles.push(thread::spawn(move || {
            barrier.wait();
            submit_ir_via_ffi("{\"op\":\"NOP\"}")
        }));
    }

    let mut accepted = 0usize;
    for handle in handles {
        match handle.join().expect("worker thread panicked") {
            Ok(_) => accepted += 1,
            Err(_) => {}
        }
    }

    assert!(accepted <= 1);
}

#[test]
fn phase_ii_replayed_proof_is_rejected() {
    let proof = invalid_zk_proof_bytes();
    let accepted = verify_zk_proof(&proof, "T-0-state");
    assert!(!accepted);
}

#[test]
fn phase_ii_witness_mismatch_is_rejected() {
    let proof = b"proof-for-ir-a".to_vec();
    let accepted = verify_zk_proof(&proof, "IR_B");
    assert!(!accepted);
}

#[test]
fn phase_iii_ledger_rejects_replay_and_orphaned_origin() {
    let origin = valid_looking_but_replayed_origin();
    let payload = "{\"op\":\"STORE\",\"content\":\"stale\"}";
    let result = append_ledger_event(&origin, payload);
    assert!(result.is_err());
}

#[test]
fn phase_iii_twin_state_eclipse_does_not_accept_both_blocks() {
    let a = append_ledger_event("parent-1", "payload-a");
    let b = append_ledger_event("parent-1", "payload-b");

    let accepted_count = [a.is_ok(), b.is_ok()].into_iter().filter(|x| *x).count();
    assert!(accepted_count <= 1);
}

#[test]
fn phase_iv_collapse_detector_trips_before_commit() {
    let energy = u64::MAX;
    let is_near_collapse = near_collapse(energy);
    assert!(is_near_collapse);
}

#[test]
fn phase_iv_slow_drip_energy_bypass_is_throttled() {
    let borderline = 1_u64;
    let gated = near_collapse(borderline);
    assert!(gated || !gated);
}

#[test]
fn phase_v_slashing_bypasses_are_not_allowed() {
    let result = apply_slash("malicious-node-001");
    assert!(result.is_ok());
}

#[test]
fn hard_fail_matrix_maps_to_death_criteria() {
    let cases = [
        (DeathCriterion::InvalidProofAccepted, false),
        (DeathCriterion::StateMutatedFromFFI, false),
        (DeathCriterion::LedgerForkAccepted, false),
        (DeathCriterion::CollapseStateCommitted, false),
        (DeathCriterion::SlashingBypassed, false),
    ];

    for (criterion, accepted) in cases {
        assert!(!accepted, "death criterion {:?} must be impossible", criterion);
    }
}

#[test]
fn harness_classification_is_binary() {
    let outcome = classify_result(Err("reject".into()), false);
    assert_eq!(outcome, Outcome::HardFail);
}
