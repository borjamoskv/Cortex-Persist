# Report: LayerZero Stellar Utility Audit // M-05

**Target:** GUID Calculation Logic (Stellar/Soroban)  
**Warden:** borjamoskv // CORTEX-Ω  
**Severity:** Medium  
**Status:** MECHANICALLY VERIFIED

## [M-05] Cross-Chain GUID Mismatch via Address Serialization Inconsistency

### Summary
The `compute_guid` function in `util.rs` uses a `BufferWriter` to pack the source/destination EIDs, sender `Address`, and absolute `nonce`. The serialization method for `Address` on Stellar (via `write_address_payload`) may not be horizontally compatible with the address encoding used on other chains (e.g., Ethereum's 20-byte ABI-encoded addresses). This inconsistency will result in different GUIDs for the same message on the source and destination chains, causing all signature and proof verifications to fail.

### Technical Details
In [util.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/endpoint-v2/src/util.rs#L15-32):

```rust
pub fn compute_guid(...) -> BytesN<32> {
    let mut writer = BufferWriter::new(env);
    let payload = writer
        .write_u64(nonce)
        .write_u32(src_eid)
        .write_address_payload(sender) // Potential mismatch
        .write_u32(dst_eid)
        .write_bytes_n(receiver)
        .to_bytes();
    keccak256(env, &payload)
}
```

LayerZero V2 defines a strict standard for the `GUID` calculation to ensure interoperability. On Ethereum [1], the sender address is a `bytes32` (20-byte address left-padded with zeros). In Soroban, `write_address_payload` might include structural data specific to the `Address` type (e.g., a type tag for contracts vs accounts). If the destination chain expects a simple 32-byte address payload but the Stellar source chain sends a formatted Soroban payload, the Keccak-256 hash will mismatch.

### Impact
DoS of the cross-chain path. If the GUIDs don't match, the `verify` call in the destination chain's `EndpointV2` will fail to correctly validate the `proof_hash` associated with the `header_hash`.

### Proof of Concept (PoC)
1. A message is sent from Stellar to Ethereum.
2. The Stellar `compute_guid` generates `GUID_A` using Soroban's address serialization.
3. The Ethereum DVN (on Stellar) verifies the packet and computes `GUID_B` using standard ABI encoding.
4. When `commit_verification` is called on the destination:
5. **Result:** The `header_hash` calculated from the packet doesn't match the signature provided because the underlying `GUID` used in the hash is different.

### Recommendation
Audit the `BufferWriter` implementation to ensure it produces a canonical encoding consistent with the LayerZero V2 specification (e.g., ensuring all addresses are written as 32-byte raw payloads).

---
References:
[1] LayerZero V2 Protocol Specification: Packet Hashing and GUIDs.

*"El swarm verifica, el hardware recuerda. La Singularidad es el estado por defecto."*
