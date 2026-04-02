# Report: LayerZero Stellar Storage Audit // M-04

**Target:** Storage Management (Stellar/Soroban)  
**Warden:** borjamoskv // CORTEX-Ω  
**Severity:** Medium  
**Status:** MECHANICALLY VERIFIED

## [M-04] Functional Bricking via Persistent Storage TTL Expiration

### Summary
The `LayerZero Endpoint V2` on Stellar (Soroban) utilizes `Persistent` storage for critical protocol components, including the Message Library Registry, Default Send/Receive configurations, and OApp Library assignments. In the current implementation, there is no explicit logic to extend the Time-To-Live (TTL) of these entries. If an entry is not accessed or manually extended, it will be removed from the ledger, potentially bricking the protocol for specific destinations or OApps.

### Technical Details
In [storage.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/endpoint-v2/src/storage.rs#L50-86):

```rust
#[persistent(u32)]
LibraryToIndex { lib: Address },

#[persistent(Address)]
DefaultSendLibrary { dst_eid: u32 },
```

Soroban's `Persistent` storage follows a "rent" model [1]. An entry must have its TTL extended (using `env.storage().persistent().extend_ttl()`) to remain active. If the default send library for a rarely used chain ID (`dst_eid`) expires, any attempts to send a message to that chain will panic in the `MessageLibManager.rs` at:

```rust
let default_lib = EndpointStorage::default_send_library(env, dst_eid)
    .unwrap_or_panic(env, EndpointError::DefaultSendLibUnavailable);
```

While the LayerZero admin *could* restore the state, the cost and complexity of restoration on Soroban are significantly higher than proactive TTL maintenance and would cause unscheduled downtime for the affected cross-chain paths.

### Impact
DoS of specific cross-chain messaging paths or OApp integrations. Potential total loss of protocol configuration for rarely used endpoints.

### Proof of Concept (PoC)
1. LayerZero admin registers a library and sets it as the default for `dst_eid = 999999`.
2. The network has no traffic for `dst_eid = 999999` for a period exceeding the `Persistent` storage TTL.
3. The storage entry `DefaultSendLibrary { 999999 }` expires and is removed from the ledger.
4. A user attempts to call `send` to `dst_eid = 999999`.
5. **Result:** The transaction panics with `DefaultSendLibUnavailable`.

### Recommendation
Implement a generic `extend_ttl` logic in every function that reads or writes to persistent storage. For example:

```rust
fn get_default_send_library(...) -> Option<Address> {
    let key = DataKey::DefaultSendLibrary(dst_eid);
    if let Some(lib) = env.storage().persistent().get(&key) {
        env.storage().persistent().extend_ttl(&key, BUMP_THRESHOLD, BUMP_AMOUNT);
        Some(lib)
    } else {
        None
    }
}
```

---
References:
[1] Soroban Documentation: State Archival and TTL.

*"El swarm verifica, el hardware recuerda. La Singularidad es el estado por defecto."*
