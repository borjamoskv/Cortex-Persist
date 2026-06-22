// Causal Engine for C5-REAL
// Replaces F# Cortex.Kernel.CausalEngine and Cortex.Kernel.Babylon

pub const MAX_DIVERGENCE: u16 = 1000;

pub fn pop_count(x: u64) -> i32 {
    let mut v1 = x.wrapping_sub((x >> 1) & 0x5555555555555555);
    let mut v2 = (v1 & 0x3333333333333333) + ((v1 >> 2) & 0x3333333333333333);
    let mut v3 = (v2 + (v2 >> 4)) & 0x0f0f0f0f0f0f0f0f;
    let mut v4 = v3 + (v3 >> 8);
    let mut v5 = v4 + (v4 >> 16);
    let mut v6 = v5 + (v5 >> 32);
    (v6 & 0x7f) as i32
}

pub fn causal_distance(ancestry_overlap: u16, ledger_overlap: u16, witness_overlap: u16, temporal_overlap: u16) -> u16 {
    let ancestry_weight = 60;
    let witness_weight = 30;
    let ledger_weight = 10;
    let temporal_weight = 1;

    let score = (ancestry_overlap * ancestry_weight) +
                (witness_overlap * witness_weight) +
                (ledger_overlap * ledger_weight) +
                (temporal_overlap * temporal_weight);

    if score > MAX_DIVERGENCE {
        0
    } else {
        MAX_DIVERGENCE - score
    }
}
