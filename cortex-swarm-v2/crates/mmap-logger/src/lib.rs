#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct SegmentHeader {
    pub magic: u64,
    pub version: u32,
    pub sealed: u8,
    pub reserved: [u8; 3],
    pub segment_id: u64,
    pub start_seq: u64,
    pub end_seq: u64,
    pub record_count: u32,
    pub capacity: u32,
    pub checksum: u64,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct EvalVector {
    pub compile_ok: f32,
    pub test_delta: f32,
    pub regression_risk: f32,
    pub cost: f32,
    pub novelty: f32,
    pub lineage_depth: f32,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct EventRecord {
    pub seq: u64,              // monotonically increasing
    pub parent_seq: u64,       // Causal credit assignment
    pub hash_env: u64,         // Env Context Hash
    pub agent_id: u32,
    pub tick: u64,
    pub type_tag: u8,          // 0:Hypothesis, 1:Patch, 2:Evidence, 3:RejectedNoise, 4:KnownGood
    pub done: u8,
    pub reserved: [u8; 2],     // Alignment padding
    pub eval: EvalVector,      // Dense evaluation gradient
    pub obs_offset: u64,       // offset dentro de un slab/arena
    pub obs_len: u32,
    pub action_id: u32,
    pub model_version: u32,
    pub clock_hi: u64,         // logical clock / epoch
    pub clock_lo: u64,
}

pub mod scheduler;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_works() {
        let result = add(2, 2);
        assert_eq!(result, 4);
    }
}
