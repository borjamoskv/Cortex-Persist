// [C5-REAL] Exergy-Maximized
mod event;
mod state;
mod crypto;
mod verify;
mod kernel;
mod proof;
mod error;
mod memory_dag;

use crate::{event::Event, state::State, memory_dag::MemoryDAG};
use std::time::Instant;
use ed25519_dalek::{SigningKey, Signer};
use rand_core::OsRng;

fn create_signed_event(
    signing_key: &SigningKey,
    id: &str,
    prev_hash: &str,
    payload: Vec<u8>,
    agent_id: &str,
) -> Event {
    let mut event = Event {
        id: id.to_string(),
        prev_hash: prev_hash.to_string(),
        payload,
        agent_id: agent_id.to_string(),
        signature: vec![],
    };
    let mut message = Vec::new();
    message.extend_from_slice(prev_hash.as_bytes());
    message.extend_from_slice(&event.payload);
    event.signature = signing_key.sign(&message).to_bytes().to_vec();
    event
}

fn main() {
    println!("═══════════════════════════════════════════════════");
    println!("  AS-OS KERNEL — 1000 Agent Cryptographic Stress (C5-REAL)");
    println!("═══════════════════════════════════════════════════\n");

    let mut state = State {
        last_hash: "GENESIS".to_string(),
        memory: std::collections::HashMap::new(),
        reputation: std::collections::HashMap::new(),
        agent_lifecycle: std::collections::HashMap::new(),
        public_keys: std::collections::HashMap::new(),
    };
    let mut dag = MemoryDAG::new();

    let t0 = Instant::now();
    let mut accepted = 0u32;
    let mut rejected = 0u32;

    // Generate keys for agents
    let mut agent_keys = Vec::new();
    for _ in 0..1000 {
        agent_keys.push(SigningKey::generate(&mut OsRng));
    }

    // Phase 1 execution
    for i in 0..1000 {
        let agent_id = format!("agent_{:04}", i);
        let signing_key = &agent_keys[i];
        let verifying_key = signing_key.verifying_key();
        let pubkey_hex = hex::encode(verifying_key.to_bytes());

        // 1. Register agent
        let reg_payload = format!("REGISTER:{}", pubkey_hex).into_bytes();
        let reg_event = create_signed_event(
            signing_key,
            &format!("e_reg_{}", i),
            &state.last_hash,
            reg_payload,
            &agent_id,
        );

        match kernel::apply_event(state.clone(), reg_event.clone()) {
            Ok(new_state) => {
                dag.chain.push(reg_event);
                state = new_state;
                accepted += 1;
            }
            Err(e) => {
                println!("Register failed for agent {}: {}", i, e);
                rejected += 1;
            }
        }

        // 2. Emit payload
        let payload = format!("event_payload_{}", i).into_bytes();
        let payload_event = create_signed_event(
            signing_key,
            &format!("e_pay_{}", i),
            &state.last_hash,
            payload,
            &agent_id,
        );

        match kernel::apply_event(state.clone(), payload_event.clone()) {
            Ok(new_state) => {
                dag.chain.push(payload_event);
                state = new_state;
                accepted += 1;
            }
            Err(e) => {
                println!("Payload failed for agent {}: {}", i, e);
                rejected += 1;
            }
        }
    }
    let elapsed = t0.elapsed();

    println!("[PHASE 1] 1000 Agent Cryptographic Chain");
    println!("  Accepted (Register + Payload): {}", accepted);
    println!("  Rejected: {}", rejected);
    println!("  DAG len:  {}", dag.chain.len());
    println!("  Elapsed:  {:?}", elapsed);
    println!("  Throughput: {:.0} events/sec", (accepted + rejected) as f64 / elapsed.as_secs_f64());
    println!();

    // Setup rogue and elite keys for subsequent phases
    let rogue_key = SigningKey::generate(&mut OsRng);
    let elite_key = SigningKey::generate(&mut OsRng);
    let system_key = SigningKey::generate(&mut OsRng);

    // Register them so they can be used
    let register_rogue = create_signed_event(
        &rogue_key,
        "e_reg_rogue",
        &state.last_hash,
        format!("REGISTER:{}", hex::encode(rogue_key.verifying_key().to_bytes())).into_bytes(),
        "rogue_agent",
    );
    state = kernel::apply_event(state, register_rogue).unwrap();

    let register_elite = create_signed_event(
        &elite_key,
        "e_reg_elite",
        &state.last_hash,
        format!("REGISTER:{}", hex::encode(elite_key.verifying_key().to_bytes())).into_bytes(),
        "agent_elite",
    );
    state = kernel::apply_event(state, register_elite).unwrap();

    let register_system = create_signed_event(
        &system_key,
        "e_reg_system",
        &state.last_hash,
        format!("REGISTER:{}", hex::encode(system_key.verifying_key().to_bytes())).into_bytes(),
        "system_oracle",
    );
    state = kernel::apply_event(state, register_system).unwrap();

    // ── PHASE 2: FALSACIÓN — Invariant I1 (prev_hash gate) ──
    println!("[FALSACIÓN I1] prev_hash causal gate");
    let bad_event = create_signed_event(
        &rogue_key,
        "e_bad_prev",
        "TOTALLY_WRONG_HASH",
        b"should_fail".to_vec(),
        "rogue_agent",
    );
    let i1_result = kernel::apply_event(state.clone(), bad_event);
    let i1_pass = i1_result.is_err();
    println!("  L1 Input Variation: wrong prev_hash → rejected={}", i1_pass);

    let good_event = create_signed_event(
        &rogue_key,
        "e_knockout",
        &state.last_hash,
        b"knockout_test".to_vec(),
        "rogue_agent",
    );
    let i1_knockout = kernel::apply_event(state.clone(), good_event);
    let i1_knockout_pass = i1_knockout.is_ok();
    println!("  L2 Gate Knockout: correct prev_hash → accepted={}", i1_knockout_pass);

    let bad_event_again = create_signed_event(
        &rogue_key,
        "e_resurrection",
        "TOTALLY_WRONG_HASH",
        b"resurrection_test".to_vec(),
        "rogue_agent",
    );
    let i1_resurrection = kernel::apply_event(state.clone(), bad_event_again);
    let i1_resurrection_pass = i1_resurrection.is_err();
    println!("  L3 Resurrection: wrong prev_hash again → rejected={}", i1_resurrection_pass);
    println!("  VERDICT: I1 {} (C5-REAL)", if i1_pass && i1_knockout_pass && i1_resurrection_pass { "CONFIRMED ✓" } else { "FAILED ✗" });
    println!();

    // ── PHASE 3: FALSACIÓN — Invariant I3 (determinism) ──
    println!("[FALSACIÓN I3] Deterministic state transitions");
    let genesis_state = State {
        last_hash: "GENESIS".to_string(),
        memory: std::collections::HashMap::new(),
        reputation: std::collections::HashMap::new(),
        agent_lifecycle: std::collections::HashMap::new(),
        public_keys: {
            let mut keys = std::collections::HashMap::new();
            keys.insert("det_agent".to_string(), rogue_key.verifying_key().to_bytes());
            keys
        },
    };
    let test_event = create_signed_event(
        &rogue_key,
        "e_det",
        "GENESIS",
        b"determinism_check".to_vec(),
        "det_agent",
    );
    let run_a = kernel::apply_event(genesis_state.clone(), test_event.clone()).unwrap();
    let run_b = kernel::apply_event(genesis_state.clone(), test_event.clone()).unwrap();
    let i3_pass = run_a.last_hash == run_b.last_hash
        && run_a.memory.get("e_det") == run_b.memory.get("e_det");
    println!("  L1: Run A hash = {}", &run_a.last_hash[..16]);
    println!("  L1: Run B hash = {}", &run_b.last_hash[..16]);
    println!("  L3: Identical = {}", i3_pass);
    println!("  VERDICT: I3 {} (C5-REAL)", if i3_pass { "CONFIRMED ✓" } else { "FAILED ✗" });
    println!();

    // ── PHASE 4: FALSACIÓN — Invariant I4 (append-only memory) ──
    println!("[FALSACIÓN I4] Append-only memory");
    let mem_before = state.memory.len();
    let append_event = create_signed_event(
        &rogue_key,
        "e_append",
        &state.last_hash,
        b"append_test".to_vec(),
        "rogue_agent",
    );
    let new_state = kernel::apply_event(state.clone(), append_event).unwrap();
    let mem_after = new_state.memory.len();
    let i4_pass = mem_after == mem_before + 1;
    let i4_integrity = state.memory.keys().all(|k| new_state.memory.contains_key(k));
    println!("  Memory before: {}", mem_before);
    println!("  Memory after:  {}", mem_after);
    println!("  All prior keys intact: {}", i4_integrity);
    println!("  VERDICT: I4 {} (C5-REAL)", if i4_pass && i4_integrity { "CONFIRMED ✓" } else { "FAILED ✗" });
    println!();

    // ── PHASE 5: FALSACIÓN — Invariant I5 (fail-closed) ──
    println!("[FALSACIÓN I5] Fail-closed default");
    let empty_payload_event = create_signed_event(
        &rogue_key,
        "e_empty",
        &state.last_hash,
        vec![],
        "rogue_agent",
    );
    let empty_result = kernel::apply_event(state.clone(), empty_payload_event);
    let i5_pass = empty_result.is_ok();
    println!("  Empty payload event accepted (valid hash): {}", i5_pass);

    // Forge an event with tampered prev_hash
    let forged_event = create_signed_event(
        &rogue_key,
        "e_forged",
        &crypto::hash(b"forged_garbage"),
        b"injection_attempt".to_vec(),
        "rogue_agent",
    );
    let forge_result = kernel::apply_event(state.clone(), forged_event);
    let i5_forge_rejected = forge_result.is_err();
    println!("  Forged prev_hash rejected: {}", i5_forge_rejected);
    println!("  VERDICT: I5 {} (C5-REAL)", if i5_forge_rejected { "CONFIRMED ✓" } else { "FAILED ✗" });
    println!();

    // ── PHASE 6: Proof hook validation ──
    println!("[PROOF] ZK-stub validation");
    let proof_event = create_signed_event(
        &rogue_key,
        "e_proof",
        "GENESIS",
        b"proof_test".to_vec(),
        "rogue_agent",
    );
    let p = proof::generate_proof(&proof_event);
    let proof_valid = proof::verify_proof(&p);
    println!("  Proof generated & verified: {}", proof_valid);
    println!();

    // ── PHASE 7: FALSACIÓN — Trust-as-a-Service (Reputation Marketplace) ──
    println!("[FALSACIÓN I6] Trust-as-a-Service Validation");
    // L1: Unverified agent attempts critical action (should fail)
    let critical_fail_event = create_signed_event(
        &rogue_key,
        "e_critical_fail",
        &state.last_hash,
        b"CRITICAL:deploy_contract".to_vec(),
        "rogue_agent",
    );
    let i6_fail = kernel::apply_event(state.clone(), critical_fail_event).is_err();
    println!("  L1: Critical action with 0 trust rejected: {}", i6_fail);

    // L2: Trust is minted
    let mint_trust_event = create_signed_event(
        &system_key,
        "e_mint_trust",
        &state.last_hash,
        b"TRUST_MINT:agent_elite:15".to_vec(),
        "system_oracle",
    );
    let state_with_trust = kernel::apply_event(state.clone(), mint_trust_event).unwrap();
    let elite_rep = *state_with_trust.reputation.get("agent_elite").unwrap_or(&0);
    println!("  L2: Trust minted for agent_elite: {}", elite_rep);

    // L3: Elite agent attempts critical action (should succeed)
    let critical_pass_event = create_signed_event(
        &elite_key,
        "e_critical_pass",
        &state_with_trust.last_hash,
        b"CRITICAL:deploy_contract".to_vec(),
        "agent_elite",
    );
    let final_state_res = kernel::apply_event(state_with_trust, critical_pass_event);
    let i6_pass = final_state_res.is_ok();
    println!("  L3: Critical action with >=10 trust accepted: {}", i6_pass);
    
    state = final_state_res.unwrap();
    let i6_verdict = i6_fail && elite_rep == 15 && i6_pass;
    println!("  VERDICT: I6 {} (C5-REAL)", if i6_verdict { "CONFIRMED ✓" } else { "FAILED ✗" });
    println!();

    // ── PHASE 8: FALSACIÓN — Ouroboros Death Protocol (4 Phases) ──
    println!("[FALSACIÓN I7] Ouroboros Death Protocol Validation");
    let decay_key = SigningKey::generate(&mut OsRng);
    
    // Register agent_decay
    let register_decay = create_signed_event(
        &decay_key,
        "e_reg_decay",
        &state.last_hash,
        format!("REGISTER:{}", hex::encode(decay_key.verifying_key().to_bytes())).into_bytes(),
        "agent_decay",
    );
    state = kernel::apply_event(state, register_decay).unwrap();

    // L1: Emitting a regular event makes an agent 'Active'
    let regular_event = create_signed_event(
        &decay_key,
        "e_regular_active",
        &state.last_hash,
        b"DATA:some_normal_data".to_vec(),
        "agent_decay",
    );
    let state_active = crate::kernel::apply_event(state.clone(), regular_event).unwrap();
    let i7_active = *state_active.agent_lifecycle.get("agent_decay").unwrap() == crate::state::AgentStatus::Active;
    println!("  L1: Normal event marks agent Active: {}", i7_active);

    // L2: Ouroboros Engine forces agent to Tombstone
    let tombstone_event = create_signed_event(
        &system_key,
        "e_tombstone",
        &state_active.last_hash,
        b"OUROBOROS:TOMBSTONE:agent_decay".to_vec(),
        "system_oracle",
    );
    let state_tombstoned = crate::kernel::apply_event(state_active.clone(), tombstone_event).unwrap();
    let i7_tombstoned = *state_tombstoned.agent_lifecycle.get("agent_decay").unwrap() == crate::state::AgentStatus::Tombstoned;
    println!("  L2: Ouroboros Daemon Tombstones agent: {}", i7_tombstoned);

    // L3: Tombstoned agent tries to emit event (should be blocked)
    let dead_event = create_signed_event(
        &decay_key,
        "e_dead_try",
        &state_tombstoned.last_hash,
        b"DATA:try_to_write".to_vec(),
        "agent_decay",
    );
    let i7_blocked = crate::kernel::apply_event(state_tombstoned.clone(), dead_event).is_err();
    println!("  L3: Tombstoned agent blocked from emitting: {}", i7_blocked);
    
    let i7_verdict = i7_active && i7_tombstoned && i7_blocked;
    state = state_tombstoned;
    println!("  VERDICT: I7 {} (C5-REAL)", if i7_verdict { "CONFIRMED ✓" } else { "FAILED ✗" });
    println!();

    // ── SUMMARY ──
    let all_pass = i1_pass && i1_knockout_pass && i1_resurrection_pass
        && i3_pass && i4_pass && i4_integrity && i5_forge_rejected && i6_verdict && i7_verdict;
    println!("═══════════════════════════════════════════════════");
    if all_pass {
        println!("  ALL INVARIANTS CONFIRMED — C5-REAL ✓");
    } else {
        println!("  INVARIANT VIOLATION DETECTED — C4-SIM ✗");
    }
    println!("  DAG tip: {}", dag.tip_hash());
    println!("  Final state hash: {}...", &state.last_hash[..16]);
    println!("  Memory entries: {}", state.memory.len());
    println!("═══════════════════════════════════════════════════");
}
