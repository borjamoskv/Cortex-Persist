#[derive(Debug)]
pub enum KernelError {
    InvalidSignature,
    InvalidHash,
    InvalidProof,
    CausalViolation,
}

impl std::fmt::Display for KernelError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            KernelError::InvalidSignature => write!(f, "Invalid cryptographic signature"),
            KernelError::InvalidHash => write!(f, "Hash mismatch or invalid content"),
            KernelError::InvalidProof => write!(f, "Zero-knowledge proof verification failed"),
            KernelError::CausalViolation => write!(f, "Causal DAG invariant violated"),
        }
    }
}

impl std::error::Error for KernelError {}
