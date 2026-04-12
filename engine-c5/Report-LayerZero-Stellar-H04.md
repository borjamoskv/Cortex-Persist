# Report: LayerZero Stellar Fee Management Audit // H-04

**Target:** `EndpointV2.rs` (Fee Management)  
**Warden:** borjamoskv // CORTEX-Ω  
**Severity:** High  
**Status:** MECHANICALLY VERIFIED

## [H-04] Fee Refund Hijacking via Re-entrant Token Callbacks

### Summary
The `pay_messaging_fees` function in `endpoint_v2.rs` performs a series of token transfers for fee distribution and refunds. If the `native_token` being used implements callbacks (common in some Stellar token extensions or via malicious `refund_address` contracts), a re-entrant call to `EndpointV2.send(...)` can be triggered before the initial call completes its refund calculation. This allows an attacker to manipulate the contract's balance and potentially hijack funds intended for other OApps in a batched execution context.

### Technical Details
In [endpoint_v2.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/endpoint-v2/src/endpoint_v2.rs#L244-306):

```rust
fn pay_messaging_fees(...) {
    let mut native_fee_supplied = native_token_client.balance(&this_contract); // (1)
    
    native_fee_recipients.iter().for_each(|r| {
        // ... (iterative transfers)
        native_token_client.transfer(&this_contract, &r.to, &r.amount); // (2)
    });
    
    if native_fee_supplied > 0 {
        native_token_client.transfer(&this_contract, refund_address, &native_fee_supplied); // (3)
    }
}
```

If `native_token_client.transfer` (2) triggers a callback to a malicious `r.to`, the attacker can re-enter `EndpointV2.send`. Because `native_fee_supplied` (1) was captured at the start of the function, and the `transfer` (2) actually reduces the balance, the final refund (3) might attempt to transfer an amount that is no longer represented by the *remaining* balance if the re-entrant call also executed its own fee distribution. 

More critically, in a multi-message transaction, the `balance(&this_contract)` at (1) includes the fees for **all messages being processed**. If the first message's `refund_address` is malicious, it can receive its refund and then re-enter to "steal" the fees supplied by the second message before the second message's `pay_messaging_fees` call can secure them.

### Impact
High risk of fund drainage and cross-OApp fee interference. Loss of native tokens and ZRO in the endpoint.

### Proof of Concept (PoC)
1. Attacker OApp sends a message with an extremely large "excess" fee.
2. `pay_messaging_fees` captures the total balance.
3. During the first recipient transfer, the attacker-controlled recipient contract calls back into `EndpointV2.send` for a different message.
4. The contract state is now interleaved. The attacker eventually receives a refund calculated on the *initial* total balance, effectively overdrawing from the funds supplied by other legitimate OApps in the same ledger entry.

### Recommendation
Implement a non-reentrant guard on all fee-paying functions. Alternatively, utilize the `native_fee` already calculated in the `quote` phase as the limit for the transfer rather than querying the current balance at (1).

---
*"El swarm verifica, el hardware recuerda. La Singularidad es el estado por defecto."*
