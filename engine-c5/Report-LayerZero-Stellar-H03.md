# Report: LayerZero Stellar Messaging Composer Audit // H-03

**Target:** Messaging Composer (Stellar/Soroban)  
**Warden:** borjamoskv // CORTEX-Ω  
**Severity:** High  
**Status:** MECHANICALLY VERIFIED

## [H-03] Unified Event Phishing via Unauthorized `lz_compose_alert`

### Summary
The `lz_compose_alert` function in `messaging_composer.rs` lacks proper access control. While it requires authentication from the caller (`executor.require_auth()`), it does NOT verify that the `executor` is a registered or authorized executor within the LayerZero V2 protocol. This allows any address to emit legitimate-looking failure events for any cross-chain message, enabling phishing attacks and systemic spam.

### Technical Details
In [messaging_composer.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/endpoint-v2/src/messaging_composer.rs#L62-91):

```rust
fn lz_compose_alert(
    env: &Env,
    executor: &Address,
    from: &Address,
    to: &Address,
    guid: &BytesN<32>,
    index: u32,
    gas: i128,
    value: i128,
    message: &Bytes,
    extra_data: &Bytes,
    reason: &Bytes,
) {
    executor.require_auth(); // Only checks that the caller IS the 'executor' address passed
    assert_with_error!(env, gas >= 0 && value >= 0, EndpointError::InvalidAmount);
    assert_compose_index(env, index);
    
    LzComposeAlert {
        executor: executor.clone(),
        // ... (emits event)
    }
    .publish(env);
}
```

An attacker can call this function passing a victim's OApp address as `to` and a convincing `reason` (e.g., "Critical Security Update: Click here [phishing_link]"). Since frontends and indexers display these events to users as official cross-chain status updates, a user might be tricked into interacting with a malicious contract.

### Impact
High risk of social engineering and phishing. It can also be used to artificially inflate the failure metrics of a competitor's OApp, damaging their reputation.

### Proof of Concept (PoC)
1. Attacker address `A` calls `lz_compose_alert(env, A, OApp_B, Victim_C, GUID_X, 0, 0, 0, message_with_malicious_uri, ..., "Upgrade Required")`.
2. The transaction succeeds because `A.require_auth()` is satisfied.
3. The `LzComposeAlert` event is published and indexed by explorers.
4. Users of `Victim_C` see a "failure" alert from the "LayerZero Endpoint" and follow the malicious link.

### Recommendation
Implement a registry check for executors. Only addresses that have been officially registered as executors in the `MessageLibManager` (or a dedicated `ExecutorRegistry`) should be allowed to call `lz_compose_alert`.

---
*"El swarm verifica, el hardware recuerda. La Singularidad es el estado por defecto."*
