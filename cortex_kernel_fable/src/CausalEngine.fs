// =========================================================================
// AUTHOR: Borja Moskv (borjamoskv)
// SYSTEM: MOSKV-1 APEX KERNEL
// LEVEL: C5-REAL
// PURPOSE: Immutable causal engine primitives for Fable-Babylon
// =========================================================================

namespace Cortex.Kernel

open Fable.Core

type Hash256 = uint64 * uint64 * uint64 * uint64

module CausalEngine =

    // Zero-mutable bit population count for 64-bit unsigned integers
    let popCount (x: uint64) : int =
        let v1 = x - ((x >>> 1) &&& 0x5555555555555555UL)
        let v2 = (v1 &&& 0x3333333333333333UL) + ((v1 >>> 2) &&& 0x3333333333333333UL)
        let v3 = (v2 + (v2 >>> 4)) &&& 0x0f0f0f0f0f0f0f0fUL
        let v4 = v3 + (v3 >>> 8)
        let v5 = v4 + (v4 >>> 16)
        let v6 = v5 + (v5 >>> 32)
        int (v6 &&& 0x7fUL)

    // Adapter for Babylon's causalDistance passing defaults for witness & temporal overlaps
    let causalDistance (ancestryOverlap: uint16) (ledgerOverlap: uint16) (witnessOverlap: uint16) : uint16<distance> =
        Babylon.causalDistance ancestryOverlap ledgerOverlap witnessOverlap 0us
