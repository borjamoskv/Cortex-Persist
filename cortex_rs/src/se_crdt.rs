use pyo3::prelude::*;
use uuid::Uuid;
use sha2::{Sha256, Digest};

pub const MAX_EVIDENCE: usize = 32;

/// Semantic Lattice CRDT for Evidence-Based Swarm Synchronization.
///
/// Refactored to avoid `Copy` trait to prevent implicit large stack copying (~1.5KB).
/// Supports monotonic cryptographic compaction of sets when the buffer size reaches `MAX_EVIDENCE`.
#[pyclass(from_py_object)]
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SemanticState {
    pub active_supports: [Uuid; MAX_EVIDENCE],
    pub active_supports_len: u32,

    pub discard_evidence: [Uuid; MAX_EVIDENCE],
    pub discard_evidence_len: u32,

    pub dependencies: [Uuid; MAX_EVIDENCE],
    pub dependencies_len: u32,

    pub cryptographic_proofs: [[u8; 32]; MAX_EVIDENCE],
    pub cryptographic_proofs_len: u32,
}

#[pymethods]
impl SemanticState {
    #[new]
    pub fn new() -> Self {
        Self {
            active_supports: [Uuid::nil(); MAX_EVIDENCE],
            active_supports_len: 0,
            discard_evidence: [Uuid::nil(); MAX_EVIDENCE],
            discard_evidence_len: 0,
            dependencies: [Uuid::nil(); MAX_EVIDENCE],
            dependencies_len: 0,
            cryptographic_proofs: [[0; 32]; MAX_EVIDENCE],
            cryptographic_proofs_len: 0,
        }
    }

    pub fn add_active_support(&mut self, id_str: &str) -> PyResult<()> {
        let id = Uuid::parse_str(id_str)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        
        for i in 0..(self.active_supports_len as usize) {
            if self.active_supports[i] == id {
                return Ok(());
            }
        }
        if (self.active_supports_len as usize) >= MAX_EVIDENCE {
            // Auto-compact to free space deterministically
            self.compact_active_supports()?;
        }
        self.active_supports[self.active_supports_len as usize] = id;
        self.active_supports_len += 1;
        Ok(())
    }

    pub fn add_discard_evidence(&mut self, id_str: &str) -> PyResult<()> {
        let id = Uuid::parse_str(id_str)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        
        for i in 0..(self.discard_evidence_len as usize) {
            if self.discard_evidence[i] == id {
                return Ok(());
            }
        }
        if (self.discard_evidence_len as usize) >= MAX_EVIDENCE {
            self.compact_discard_evidence()?;
        }
        self.discard_evidence[self.discard_evidence_len as usize] = id;
        self.discard_evidence_len += 1;
        Ok(())
    }

    pub fn add_dependency(&mut self, id_str: &str) -> PyResult<()> {
        let id = Uuid::parse_str(id_str)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        
        for i in 0..(self.dependencies_len as usize) {
            if self.dependencies[i] == id {
                return Ok(());
            }
        }
        if (self.dependencies_len as usize) >= MAX_EVIDENCE {
            self.compact_dependencies()?;
        }
        self.dependencies[self.dependencies_len as usize] = id;
        self.dependencies_len += 1;
        Ok(())
    }

    pub fn add_cryptographic_proof(&mut self, proof_hex: &str) -> PyResult<()> {
        let mut proof = [0u8; 32];
        hex::decode_to_slice(proof_hex, &mut proof)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        
        for i in 0..(self.cryptographic_proofs_len as usize) {
            if self.cryptographic_proofs[i] == proof {
                return Ok(());
            }
        }
        if (self.cryptographic_proofs_len as usize) >= MAX_EVIDENCE {
            return Err(pyo3::exceptions::PyValueError::new_err("Cryptographic proofs buffer full"));
        }
        self.cryptographic_proofs[self.cryptographic_proofs_len as usize] = proof;
        self.cryptographic_proofs_len += 1;
        Ok(())
    }

    /// Compacts active supports into a single SHA-256 hash and clears the active array.
    /// The computed hash is prepended to `cryptographic_proofs` to maintain subset logic.
    pub fn compact_active_supports(&mut self) -> PyResult<()> {
        if self.active_supports_len == 0 {
            return Ok(());
        }
        let mut sorted = self.active_supports[0..(self.active_supports_len as usize)].to_vec();
        sorted.sort();

        let mut hasher = Sha256::new();
        for id in &sorted {
            hasher.update(id.as_bytes());
        }
        let hash: [u8; 32] = hasher.finalize().into();

        self.insert_cryptographic_proof_internal(hash)?;
        self.active_supports_len = 0;
        Ok(())
    }

    pub fn compact_discard_evidence(&mut self) -> PyResult<()> {
        if self.discard_evidence_len == 0 {
            return Ok(());
        }
        let mut sorted = self.discard_evidence[0..(self.discard_evidence_len as usize)].to_vec();
        sorted.sort();

        let mut hasher = Sha256::new();
        for id in &sorted {
            hasher.update(id.as_bytes());
        }
        let hash: [u8; 32] = hasher.finalize().into();

        self.insert_cryptographic_proof_internal(hash)?;
        self.discard_evidence_len = 0;
        Ok(())
    }

    pub fn compact_dependencies(&mut self) -> PyResult<()> {
        if self.dependencies_len == 0 {
            return Ok(());
        }
        let mut sorted = self.dependencies[0..(self.dependencies_len as usize)].to_vec();
        sorted.sort();

        let mut hasher = Sha256::new();
        for id in &sorted {
            hasher.update(id.as_bytes());
        }
        let hash: [u8; 32] = hasher.finalize().into();

        self.insert_cryptographic_proof_internal(hash)?;
        self.dependencies_len = 0;
        Ok(())
    }

    pub fn merge(&mut self, other: &SemanticState) -> PyResult<()> {
        for i in 0..(other.active_supports_len as usize) {
            let item = other.active_supports[i];
            let mut exists = false;
            for j in 0..(self.active_supports_len as usize) {
                if self.active_supports[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists {
                if (self.active_supports_len as usize) >= MAX_EVIDENCE {
                    self.compact_active_supports()?;
                }
                self.active_supports[self.active_supports_len as usize] = item;
                self.active_supports_len += 1;
            }
        }

        for i in 0..(other.discard_evidence_len as usize) {
            let item = other.discard_evidence[i];
            let mut exists = false;
            for j in 0..(self.discard_evidence_len as usize) {
                if self.discard_evidence[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists {
                if (self.discard_evidence_len as usize) >= MAX_EVIDENCE {
                    self.compact_discard_evidence()?;
                }
                self.discard_evidence[self.discard_evidence_len as usize] = item;
                self.discard_evidence_len += 1;
            }
        }

        for i in 0..(other.dependencies_len as usize) {
            let item = other.dependencies[i];
            let mut exists = false;
            for j in 0..(self.dependencies_len as usize) {
                if self.dependencies[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists {
                if (self.dependencies_len as usize) >= MAX_EVIDENCE {
                    self.compact_dependencies()?;
                }
                self.dependencies[self.dependencies_len as usize] = item;
                self.dependencies_len += 1;
            }
        }

        for i in 0..(other.cryptographic_proofs_len as usize) {
            let item = other.cryptographic_proofs[i];
            let mut exists = false;
            for j in 0..(self.cryptographic_proofs_len as usize) {
                if self.cryptographic_proofs[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists {
                if (self.cryptographic_proofs_len as usize) >= MAX_EVIDENCE {
                    return Err(pyo3::exceptions::PyValueError::new_err("Cryptographic proofs buffer full during merge"));
                }
                self.cryptographic_proofs[self.cryptographic_proofs_len as usize] = item;
                self.cryptographic_proofs_len += 1;
            }
        }

        Ok(())
    }

    pub fn dominates(&self, other: &SemanticState) -> bool {
        for i in 0..(other.active_supports_len as usize) {
            let item = other.active_supports[i];
            let mut exists = false;
            for j in 0..(self.active_supports_len as usize) {
                if self.active_supports[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists {
                return false;
            }
        }

        for i in 0..(other.discard_evidence_len as usize) {
            let item = other.discard_evidence[i];
            let mut exists = false;
            for j in 0..(self.discard_evidence_len as usize) {
                if self.discard_evidence[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists {
                return false;
            }
        }

        for i in 0..(other.dependencies_len as usize) {
            let item = other.dependencies[i];
            let mut exists = false;
            for j in 0..(self.dependencies_len as usize) {
                if self.dependencies[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists {
                return false;
            }
        }

        for i in 0..(other.cryptographic_proofs_len as usize) {
            let item = other.cryptographic_proofs[i];
            let mut exists = false;
            for j in 0..(self.cryptographic_proofs_len as usize) {
                if self.cryptographic_proofs[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists {
                return false;
            }
        }

        true
    }

    #[getter]
    pub fn active_supports(&self) -> Vec<String> {
        self.active_supports[0..(self.active_supports_len as usize)]
            .iter()
            .map(|id| id.to_string())
            .collect()
    }

    #[getter]
    pub fn discard_evidence(&self) -> Vec<String> {
        self.discard_evidence[0..(self.discard_evidence_len as usize)]
            .iter()
            .map(|id| id.to_string())
            .collect()
    }

    #[getter]
    pub fn dependencies(&self) -> Vec<String> {
        self.dependencies[0..(self.dependencies_len as usize)]
            .iter()
            .map(|id| id.to_string())
            .collect()
    }

    #[getter]
    pub fn cryptographic_proofs(&self) -> Vec<String> {
        self.cryptographic_proofs[0..(self.cryptographic_proofs_len as usize)]
            .iter()
            .map(|p| hex::encode(p))
            .collect()
    }
}

impl SemanticState {
    fn insert_cryptographic_proof_internal(&mut self, proof: [u8; 32]) -> PyResult<()> {
        for i in 0..(self.cryptographic_proofs_len as usize) {
            if self.cryptographic_proofs[i] == proof {
                return Ok(());
            }
        }
        if (self.cryptographic_proofs_len as usize) >= MAX_EVIDENCE {
            return Err(pyo3::exceptions::PyValueError::new_err("Cryptographic proofs buffer full"));
        }
        self.cryptographic_proofs[self.cryptographic_proofs_len as usize] = proof;
        self.cryptographic_proofs_len += 1;
        Ok(())
    }
}

impl Default for SemanticState {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_merge_commutativity() {
        let u1 = "67e55044-10b1-426f-9247-bb680e5fe0c8";
        let u2 = "a1a2a3a4-b1b2-c1c2-d1d2-d3d4d5d6d7d8";
        let u3 = "00000000-0000-0000-0000-000000000000";

        let mut s1 = SemanticState::new();
        s1.add_active_support(u1).unwrap();
        s1.add_discard_evidence(u2).unwrap();

        let mut s2 = SemanticState::new();
        s2.add_active_support(u3).unwrap();
        s2.add_dependency(u1).unwrap();

        let mut s1_merge_s2 = s1.clone();
        s1_merge_s2.merge(&s2).unwrap();

        let mut s2_merge_s1 = s2.clone();
        s2_merge_s1.merge(&s1).unwrap();

        assert_eq!(s1_merge_s2, s2_merge_s1);
        assert!(s1_merge_s2.active_supports().contains(&u1.to_string()));
        assert!(s1_merge_s2.active_supports().contains(&u3.to_string()));
        assert!(s1_merge_s2.discard_evidence().contains(&u2.to_string()));
        assert!(s1_merge_s2.dependencies().contains(&u1.to_string()));
    }

    #[test]
    fn test_merge_idempotency() {
        let u1 = "67e55044-10b1-426f-9247-bb680e5fe0c8";
        let mut s1 = SemanticState::new();
        s1.add_active_support(u1).unwrap();

        let mut s2 = s1.clone();
        s2.merge(&s1).unwrap();

        assert_eq!(s1, s2);
    }

    #[test]
    fn test_dominance() {
        let u1 = "67e55044-10b1-426f-9247-bb680e5fe0c8";
        let u2 = "a1a2a3a4-b1b2-c1c2-d1d2-d3d4d5d6d7d8";

        let mut s1 = SemanticState::new();
        s1.add_active_support(u1).unwrap();
        s1.add_discard_evidence(u2).unwrap();

        let mut s2 = SemanticState::new();
        s2.add_active_support(u1).unwrap();

        assert!(s1.dominates(&s2));
        assert!(!s2.dominates(&s1));
    }

    #[test]
    fn test_compaction() {
        let mut s = SemanticState::new();
        // Insert more than MAX_EVIDENCE items to trigger compaction
        for i in 0..(MAX_EVIDENCE + 2) {
            let id = Uuid::new_v4().to_string();
            s.add_active_support(&id).unwrap();
        }
        // Active supports should be reset to 2 (the overflow items)
        assert_eq!(s.active_supports_len, 2);
        // Cryptographic proofs should now contain the compaction hash
        assert_eq!(s.cryptographic_proofs_len, 1);
    }
}
