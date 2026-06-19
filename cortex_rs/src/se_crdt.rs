use pyo3::prelude::*;
use uuid::Uuid;
use sha2::{Sha256, Digest};

pub const MAX_EVIDENCE: usize = 32;

#[pyclass(from_py_object)]
#[derive(Debug, Clone, PartialEq, Eq)]
#[repr(C)]
pub struct EvidenceState {
    pub active_supports: [Uuid; MAX_EVIDENCE],
    pub active_supports_len: u32,

    pub discard_evidence: [Uuid; MAX_EVIDENCE],
    pub discard_evidence_len: u32,

    pub dependencies: [Uuid; MAX_EVIDENCE],
    pub dependencies_len: u32,
}

#[pymethods]
impl EvidenceState {
    #[new]
    pub fn new() -> Self {
        Self {
            active_supports: [Uuid::nil(); MAX_EVIDENCE],
            active_supports_len: 0,
            discard_evidence: [Uuid::nil(); MAX_EVIDENCE],
            discard_evidence_len: 0,
            dependencies: [Uuid::nil(); MAX_EVIDENCE],
            dependencies_len: 0,
        }
    }
}

impl Default for EvidenceState {
    fn default() -> Self {
        Self::new()
    }
}

#[pyclass(from_py_object)]
#[derive(Debug, Clone, PartialEq, Eq)]
#[repr(C)]
pub struct ProvenanceState {
    pub cryptographic_proofs: [[u8; 32]; MAX_EVIDENCE],
    pub cryptographic_proofs_len: u32,

    // Semantic preservation of compacted state
    pub compacted_active_supports: u32,
    pub compacted_discard_evidence: u32,
    pub compacted_dependencies: u32,

    // Causal clock / event epoch travels with the state
    pub event_epoch: u64,
}

#[pymethods]
impl ProvenanceState {
    #[new]
    pub fn new() -> Self {
        Self {
            cryptographic_proofs: [[0; 32]; MAX_EVIDENCE],
            cryptographic_proofs_len: 0,
            compacted_active_supports: 0,
            compacted_discard_evidence: 0,
            compacted_dependencies: 0,
            event_epoch: 0,
        }
    }
}

impl Default for ProvenanceState {
    fn default() -> Self {
        Self::new()
    }
}

/// Semantic Lattice CRDT for Evidence-Based Swarm Synchronization.
///
/// Splitted into EvidenceState and ProvenanceState.
/// Compaction preserves the semantic footprint in ProvenanceState.
#[pyclass(from_py_object)]
#[derive(Debug, Clone, PartialEq, Eq)]
#[repr(C)]
pub struct SemanticState {
    #[pyo3(get, set)]
    pub evidence: EvidenceState,
    #[pyo3(get, set)]
    pub provenance: ProvenanceState,
}

#[pymethods]
impl SemanticState {
    #[new]
    pub fn new() -> Self {
        Self {
            evidence: EvidenceState::new(),
            provenance: ProvenanceState::new(),
        }
    }

    pub fn set_event_epoch(&mut self, epoch: u64) {
        self.provenance.event_epoch = epoch;
    }

    pub fn get_event_epoch(&self) -> u64 {
        self.provenance.event_epoch
    }

    pub fn add_active_support(&mut self, id_str: &str) -> PyResult<()> {
        let id = Uuid::parse_str(id_str)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        
        for i in 0..(self.evidence.active_supports_len as usize) {
            if self.evidence.active_supports[i] == id {
                return Ok(());
            }
        }
        if (self.evidence.active_supports_len as usize) >= MAX_EVIDENCE {
            return Err(pyo3::exceptions::PyBufferError::new_err("active_supports buffer full, requires explicit compaction"));
        }
        self.evidence.active_supports[self.evidence.active_supports_len as usize] = id;
        self.evidence.active_supports_len += 1;
        Ok(())
    }

    pub fn add_discard_evidence(&mut self, id_str: &str) -> PyResult<()> {
        let id = Uuid::parse_str(id_str)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        
        for i in 0..(self.evidence.discard_evidence_len as usize) {
            if self.evidence.discard_evidence[i] == id {
                return Ok(());
            }
        }
        if (self.evidence.discard_evidence_len as usize) >= MAX_EVIDENCE {
            return Err(pyo3::exceptions::PyBufferError::new_err("discard_evidence buffer full, requires explicit compaction"));
        }
        self.evidence.discard_evidence[self.evidence.discard_evidence_len as usize] = id;
        self.evidence.discard_evidence_len += 1;
        Ok(())
    }

    pub fn add_dependency(&mut self, id_str: &str) -> PyResult<()> {
        let id = Uuid::parse_str(id_str)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        
        for i in 0..(self.evidence.dependencies_len as usize) {
            if self.evidence.dependencies[i] == id {
                return Ok(());
            }
        }
        if (self.evidence.dependencies_len as usize) >= MAX_EVIDENCE {
            return Err(pyo3::exceptions::PyBufferError::new_err("dependencies buffer full, requires explicit compaction"));
        }
        self.evidence.dependencies[self.evidence.dependencies_len as usize] = id;
        self.evidence.dependencies_len += 1;
        Ok(())
    }

    pub fn add_cryptographic_proof(&mut self, proof_hex: &str) -> PyResult<()> {
        let mut proof = [0u8; 32];
        hex::decode_to_slice(proof_hex, &mut proof)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        self.insert_cryptographic_proof_internal(proof)
    }

    /// Compacts active supports. Demonstrates semantic equivalence by migrating footprint to provenance.
    pub fn compact_active_supports(&mut self, ledger_proof_hex: &str) -> PyResult<()> {
        if self.evidence.active_supports_len == 0 {
            return Ok(());
        }
        let mut proof = [0u8; 32];
        hex::decode_to_slice(ledger_proof_hex, &mut proof)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid proof format: {}", e)))?;

        self.insert_cryptographic_proof_internal(proof)?;
        self.provenance.compacted_active_supports += self.evidence.active_supports_len;
        self.evidence.active_supports_len = 0;
        Ok(())
    }

    pub fn compact_discard_evidence(&mut self, ledger_proof_hex: &str) -> PyResult<()> {
        if self.evidence.discard_evidence_len == 0 {
            return Ok(());
        }
        let mut proof = [0u8; 32];
        hex::decode_to_slice(ledger_proof_hex, &mut proof)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid proof format: {}", e)))?;

        self.insert_cryptographic_proof_internal(proof)?;
        self.provenance.compacted_discard_evidence += self.evidence.discard_evidence_len;
        self.evidence.discard_evidence_len = 0;
        Ok(())
    }

    pub fn compact_dependencies(&mut self, ledger_proof_hex: &str) -> PyResult<()> {
        if self.evidence.dependencies_len == 0 {
            return Ok(());
        }
        let mut proof = [0u8; 32];
        hex::decode_to_slice(ledger_proof_hex, &mut proof)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid proof format: {}", e)))?;

        self.insert_cryptographic_proof_internal(proof)?;
        self.provenance.compacted_dependencies += self.evidence.dependencies_len;
        self.evidence.dependencies_len = 0;
        Ok(())
    }

    pub fn merge(&mut self, other: &SemanticState) -> PyResult<()> {
        // Merge causal epoch (monotonic)
        self.provenance.event_epoch = std::cmp::max(self.provenance.event_epoch, other.provenance.event_epoch);

        // Merge footprint (monotonic, take max to avoid double counting if merged multiple times, 
        // though logically they are sets. For counts, max is safer in CRDTs assuming same compaction history, 
        // but true set union of compacted elements is lost. Max preserves minimum provenance.)
        self.provenance.compacted_active_supports = std::cmp::max(self.provenance.compacted_active_supports, other.provenance.compacted_active_supports);
        self.provenance.compacted_discard_evidence = std::cmp::max(self.provenance.compacted_discard_evidence, other.provenance.compacted_discard_evidence);
        self.provenance.compacted_dependencies = std::cmp::max(self.provenance.compacted_dependencies, other.provenance.compacted_dependencies);

        for i in 0..(other.evidence.active_supports_len as usize) {
            let item = other.evidence.active_supports[i];
            let mut exists = false;
            for j in 0..(self.evidence.active_supports_len as usize) {
                if self.evidence.active_supports[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists {
                if (self.evidence.active_supports_len as usize) >= MAX_EVIDENCE {
                    return Err(pyo3::exceptions::PyBufferError::new_err("active_supports buffer full during merge"));
                }
                self.evidence.active_supports[self.evidence.active_supports_len as usize] = item;
                self.evidence.active_supports_len += 1;
            }
        }

        for i in 0..(other.evidence.discard_evidence_len as usize) {
            let item = other.evidence.discard_evidence[i];
            let mut exists = false;
            for j in 0..(self.evidence.discard_evidence_len as usize) {
                if self.evidence.discard_evidence[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists {
                if (self.evidence.discard_evidence_len as usize) >= MAX_EVIDENCE {
                    return Err(pyo3::exceptions::PyBufferError::new_err("discard_evidence buffer full during merge"));
                }
                self.evidence.discard_evidence[self.evidence.discard_evidence_len as usize] = item;
                self.evidence.discard_evidence_len += 1;
            }
        }

        for i in 0..(other.evidence.dependencies_len as usize) {
            let item = other.evidence.dependencies[i];
            let mut exists = false;
            for j in 0..(self.evidence.dependencies_len as usize) {
                if self.evidence.dependencies[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists {
                if (self.evidence.dependencies_len as usize) >= MAX_EVIDENCE {
                    return Err(pyo3::exceptions::PyBufferError::new_err("dependencies buffer full during merge"));
                }
                self.evidence.dependencies[self.evidence.dependencies_len as usize] = item;
                self.evidence.dependencies_len += 1;
            }
        }

        for i in 0..(other.provenance.cryptographic_proofs_len as usize) {
            let item = other.provenance.cryptographic_proofs[i];
            let mut exists = false;
            for j in 0..(self.provenance.cryptographic_proofs_len as usize) {
                if self.provenance.cryptographic_proofs[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists {
                if (self.provenance.cryptographic_proofs_len as usize) >= MAX_EVIDENCE {
                    return Err(pyo3::exceptions::PyValueError::new_err("Cryptographic proofs buffer full during merge"));
                }
                self.provenance.cryptographic_proofs[self.provenance.cryptographic_proofs_len as usize] = item;
                self.provenance.cryptographic_proofs_len += 1;
            }
        }

        Ok(())
    }

    pub fn dominates(&self, other: &SemanticState) -> bool {
        if self.provenance.event_epoch < other.provenance.event_epoch {
            return false;
        }

        if self.provenance.compacted_active_supports < other.provenance.compacted_active_supports ||
           self.provenance.compacted_discard_evidence < other.provenance.compacted_discard_evidence ||
           self.provenance.compacted_dependencies < other.provenance.compacted_dependencies {
            return false;
        }

        for i in 0..(other.evidence.active_supports_len as usize) {
            let item = other.evidence.active_supports[i];
            let mut exists = false;
            for j in 0..(self.evidence.active_supports_len as usize) {
                if self.evidence.active_supports[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists { return false; }
        }

        for i in 0..(other.evidence.discard_evidence_len as usize) {
            let item = other.evidence.discard_evidence[i];
            let mut exists = false;
            for j in 0..(self.evidence.discard_evidence_len as usize) {
                if self.evidence.discard_evidence[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists { return false; }
        }

        for i in 0..(other.evidence.dependencies_len as usize) {
            let item = other.evidence.dependencies[i];
            let mut exists = false;
            for j in 0..(self.evidence.dependencies_len as usize) {
                if self.evidence.dependencies[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists { return false; }
        }

        for i in 0..(other.provenance.cryptographic_proofs_len as usize) {
            let item = other.provenance.cryptographic_proofs[i];
            let mut exists = false;
            for j in 0..(self.provenance.cryptographic_proofs_len as usize) {
                if self.provenance.cryptographic_proofs[j] == item {
                    exists = true;
                    break;
                }
            }
            if !exists { return false; }
        }

        true
    }

    #[getter]
    pub fn active_supports(&self) -> Vec<String> {
        self.evidence.active_supports[0..(self.evidence.active_supports_len as usize)]
            .iter()
            .map(|id| id.to_string())
            .collect()
    }

    #[getter]
    pub fn discard_evidence(&self) -> Vec<String> {
        self.evidence.discard_evidence[0..(self.evidence.discard_evidence_len as usize)]
            .iter()
            .map(|id| id.to_string())
            .collect()
    }

    #[getter]
    pub fn dependencies(&self) -> Vec<String> {
        self.evidence.dependencies[0..(self.evidence.dependencies_len as usize)]
            .iter()
            .map(|id| id.to_string())
            .collect()
    }

    #[getter]
    pub fn cryptographic_proofs(&self) -> Vec<String> {
        self.provenance.cryptographic_proofs[0..(self.provenance.cryptographic_proofs_len as usize)]
            .iter()
            .map(|p| hex::encode(p))
            .collect()
    }
}

impl SemanticState {
    fn insert_cryptographic_proof_internal(&mut self, proof: [u8; 32]) -> PyResult<()> {
        for i in 0..(self.provenance.cryptographic_proofs_len as usize) {
            if self.provenance.cryptographic_proofs[i] == proof {
                return Ok(());
            }
        }
        if (self.provenance.cryptographic_proofs_len as usize) >= MAX_EVIDENCE {
            return Err(pyo3::exceptions::PyValueError::new_err("Cryptographic proofs buffer full"));
        }
        self.provenance.cryptographic_proofs[self.provenance.cryptographic_proofs_len as usize] = proof;
        self.provenance.cryptographic_proofs_len += 1;
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
        for _ in 0..MAX_EVIDENCE {
            let id = Uuid::new_v4().to_string();
            s.add_active_support(&id).unwrap();
        }
        
        let mock_proof = hex::encode([0xAA; 32]);
        s.compact_active_supports(&mock_proof).unwrap();
        
        // Active supports should be reset, but provenance preserves the count
        assert_eq!(s.evidence.active_supports_len, 0);
        assert_eq!(s.provenance.compacted_active_supports, MAX_EVIDENCE as u32);
        
        assert_eq!(s.provenance.cryptographic_proofs_len, 1);
        assert_eq!(s.cryptographic_proofs()[0], mock_proof);
    }
}
