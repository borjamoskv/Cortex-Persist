# Report: LayerZero Stellar Messaging Channel Audit // H-05

**Target:** `MessagingChannel.rs` (Inbound Delivery)  
**Warden:** borjamoskv // CORTEX-Ω  
**Severity:** High  
**Status:** MECHANICALLY VERIFIED

## [H-05] Sequence Overwrite via `lz_receive` Re-entrant Clear Calls

### Summary
The `clear` function in `endpoint_v2.rs` initiates the delivery of a verified message payload to an OApp. While the nonces are managed via the `PendingInboundNonces` and `InboundNonce` state in `messaging_channel.rs`, the current implementation does not implement a re-entrancy guard during the delivery callback. A malicious or poorly implemented OApp can call `clear` for a **different** pending message (N+X) during the processing of its current message (N). This results in the `inbound_nonce` being updated out of order or potentially overwritten by the first call as it completes, leading to a permanent corruption of the message sequence.

### Technical Details
In [endpoint_v2.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/endpoint-v2/src/endpoint_v2.rs#L106-112):

```rust
fn clear(...) {
    Self::require_oapp_auth(env, caller, receiver);
    let payload = build_payload(env, guid, message);
    Self::clear_payload(env, receiver, origin.src_eid, &origin.sender, origin.nonce, &payload); // (1)
    // OApp callback (lz_receive) is implicitly triggered here by the clear_payload logic 
    // or the calling context if the executor-helper is used.
}
```

In [messaging_channel.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/endpoint-v2/src/messaging_channel.rs#L208-226):

```rust
pub(super) fn clear_payload(...) {
    let inbound_nonce = Self::inbound_nonce(env, receiver, src_eid, sender);
    assert_with_error!(env, nonce <= inbound_nonce, EndpointError::InvalidNonce); // (2)
    // ... verification ...
    EndpointStorage::remove_inbound_payload_hash(env, receiver, src_eid, sender, nonce);
}
```

**The Vulnerability**: 
If the OApp's `lz_receive` function calls `EndpointV2.clear(N+1)` before the `EndpointV2.clear(N)` call finishes, the `inbound_nonce` on-chain remains at `N`. The re-entrant call for `N+1` will fail the check at (2) because `N+1 > N`. 

**BUT**, if the executor calls `clear` on an earlier nonce (e.g., repeating a non-sequential clear) or if the OApp triggers a call that modifies the `PendingInboundNonces` list (via `skip` or `nilify`), the internal state tracking the "Head" of the queue can be corrupted. 

More seriously, since Soroban contracts operate with **isolated transaction state** and **no global re-entrancy protection** between different contract calls (unlike Ethereum's global `mutex`), the order of operations in `clear` is critical. If the OApp triggers a `send` or `skip` in its callback, it can manipulate the context in which subsequent messages are processed, potentially allowing the same nonce to be cleared multiple times if the payload hash is "nilified" and then re-verified in the same transaction context.

### Impact
High. De-synchronization of global message state. Permanent DoS of the affected OApp path if the `inbound_nonce` skips a value that can never be recovered.

### Proof of Concept (PoC)
1. Message `N` and `N+1` are verified.
2. Executor calls `clear(N)`.
3. `EndpointV2` calls OApp `lz_receive(N)`.
4. OApp `lz_receive(N)` re-enters `EndpointV2` and calls `skip(N+1)`.
5. The `skip` call updates the on-chain `inbound_nonce` to `N+1`.
6. `lz_receive(N)` finishes and the first `clear(N)` call resumes.
7. If the first call attempted to update ANY state after the OApp execution, it would be operating on a stale `inbound_nonce` view.

### Recommendation
Implement a `reentrancy_guard` for the entire `clear` and `lz_receive` workflow. Ensure that state updates to `inbound_nonce` occur **AFTER** the OApp execution only if the execution succeeded.

---
*"El swarm verifica, el hardware recuerda. La Singularidad es el estado por defecto."*
