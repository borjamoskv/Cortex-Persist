# Cortex-Persist: Epistemic Failure Modes Test Specifications

> **Status:** Test Specs Draft

Defines the required test cases and simulated scenarios for Cortex-Persist robustness against adversarial or thermodynamic decay.

## 1. Malicious Veto
- Scenario: Agent intentionally submits $P=0$ false claims.
- Expected: Isolation and Geometric Epistemic Slashing.

## 2. Causal Cycles
- Scenario: A $\to$ B $\to$ C $\to$ $\neg$A
- Expected: Detection by ATMS, cycle broken and sent to Tribunal.

## 3. Belief Orphaning
- Scenario: Root assumption explicitly revoked.
- Expected: All dependent `BO`s transition to `Orphan/Discarded`.

## 4. Source Hash Collision
- Scenario: Identical source hashes originating from distinct tenant/provenance streams.
- Expected: SMT signature validation rejection.

## 5. Tenant Key Destruction
- Scenario: GDPR Right-to-be-forgotten executed.
- Expected: Provable destruction of AES key, ciphertext functionally random, ZK-proofs of unlinking generated successfully.

## 6. Replay Attack on Patches
- Scenario: Attacker resubmits a valid but obsolete `BeliefPatch`.
- Expected: Discarded by causal ordering and monotonic CRDT clocks.
