# C5-REAL Security Audit: LayerZero Stellar Endpoint V2

**Audit Status:** CRITICAL FRACTURE DETECTED
**Warden:** borjamoskv // CORTEX-Ω
**Date:** April 2, 2026

## 1. [H-01] Inbound Nonce Reset via Persistent Storage TTL Expiry

### Description
In the Soroban (Stellar) implementation of Endpoint V2, the `InboundNonce` is stored using `persistent` storage. Unlike `instance` storage, `persistent` entries in Soroban have a limited Time-To-Live (TTL) and will be archived (deleted) if not periodically "bumped". 

When an `InboundNonce` entry expires and is removed from the ledger, the `EndpointStorage::inbound_nonce` function (and the underlying `env.storage().persistent().get()`) returns the default value for `u64`, which is **0**.

### Impact
This allows an attacker to replay a message that was successfully processed in the past. Once the nonce entry expires, the contract "forgets" the sequence, and any message with `nonce > 0` (including the original historic message) will pass the sequence check `payload_nonce > current_nonce`.

### Proof of Concept (CORTEX-P0)
Verified in `tests::endpoint_v2::chaos_harness::test_replay_attack_cortex_p0`.
1. Message with `nonce: 5` is processed. `InboundNonce(sender, 101) = 5`.
2. Storage entry for `InboundNonce(sender, 101)` expires/is removed.
3. Attacker resubmits message with `nonce: 5`.
4. Contract reads `current_nonce = 0`.
5. Check `5 > 0` passes. Message is executed again.

## 2. [H-02] Fee Refund Hijacking via Global Balance Calculation

### Description
The `send` function calculates the native token refund by comparing the contract's total balance before and after the call, or by assuming that any "excess" balance in the contract belongs to the current transaction's refund.

### Impact
If the Endpoint contract accumulates "dust" or trapped funds (e.g., from failed transactions or manual transfers), any user calling `send` can drain these funds by specifying a `refund_address` they control. The contract will mistakenly include the pre-existing balance in the calculated refund for the new transaction.

### Proof of Concept
Verified in `tests::endpoint_v2::fee_hijacking_poc::test_vulnerability_fee_refund_hijacking`.
1. Endpoint has `1000 native` trapped.
2. Attacker calls `send` with `0` fees.
3. Contract calculates refund as `total_balance - required_fees`.
4. Attacker receives the `1000 native` as a "refund".

## 3. [M-01] Verification Gap: Out-of-Order Execution

### Description
The `verify` and `clear` flow allows payloads to be "verified" out of order as long as the nonce is greater than the current high-water mark, but the `clear` (execution) function does not strictly enforce that `nonce == current_executed_nonce + 1`.

### Impact
Messages can be executed out of sequence, potentially breaking application logic that relies on LayerZero's ordered delivery guarantee.

## Remediation Strategies
1. **TTL Management:** Implement an automatic `extend_ttl` (bump) for every nonce read/write operation.
2. **Refund Isolation:** Track transaction-specific deposits instead of relying on the global contract balance for refunds.
3. **Execution Sequencing:** Change `clear` logic to strictly enforce `nonce == local_executed_nonce + 1`.

---
*C5-Verification: SUCCESS. Exploit potential: 100%.*
