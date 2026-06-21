use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const E_CRIT: u64 = 10_000;
pub const SAFETY_MARGIN: u64 = 250;

pub fn hash_bytes(data: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(data);
    hasher.finalize().into()
}

pub fn hash_u64s(parts: &[u64]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    for part in parts {
        hasher.update(part.to_le_bytes());
    }
    hasher.finalize().into()
}

pub fn hex32(bytes: &[u8; 32]) -> String {
    let mut out = String::with_capacity(64);
    for b in bytes {
        use core::fmt::Write as _;
        let _ = write!(&mut out, "{:02x}", b);
    }
    out
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum Event {
    LedgerForkCascade,
    ZkCollisionAttempt,
    FfiOverflowSpike,
    CollapseThresholdOscillation,
    ConcurrencySingularity,
    Unknown(String),
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum CollapseReason {
    ZkAcceptedInvalidProof,
    EnergyExceeded,
    LedgerForkAccepted,
    MemoryViolation,
    NonDeterminismDetected,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum KernelResult {
    Accepted,
    Rejected,
    Collapse { reason: CollapseReason },
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct TraceStats {
    pub accepted: u64,
    pub rejected: u64,
    pub commits: u64,
    pub collapse: bool,
    pub events: u64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReplayUniverse {
    pub seed: u64,
    pub epoch: u64,
    pub event_index: u64,
    pub kernel_hash: [u8; 32],
    pub ledger_root: [u8; 32],
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct UniverseReport {
    pub seed: u64,
    pub epoch: u64,
    pub kernel_hash: String,
    pub ledger_root: String,
    pub events: u64,
    pub accepted: u64,
    pub rejected: u64,
    pub collapse: bool,
    pub attestation: String,
}
