use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Sha256, Digest};
use std::collections::HashMap;

#[pyclass(from_py_object)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SmtLeaf {
    #[pyo3(get, set)]
    pub path: String,       // Hex-encoded 32-byte key
    #[pyo3(get, set)]
    pub value_hash: String, // Hex-encoded 32-byte value hash
}

#[pymethods]
impl SmtLeaf {
    #[new]
    pub fn new(path: String, value_hash: String) -> Self {
        SmtLeaf { path, value_hash }
    }
}

/// Sparse Merkle Tree (SMT) implementation with 256 levels.
/// Provides cryptographic integrity proofs in O(log N).
#[pyclass(from_py_object)]
#[derive(Debug, Clone)]
pub struct SparseMerkleTree {
    pub leaves: HashMap<String, String>,          // path -> value_hash
    pub default_hashes: Vec<[u8; 32]>,           // precomputed default hashes for each level
    pub tree_nodes: HashMap<String, [u8; 32]>,   // path_prefix (binary string) -> hash
}

impl Default for SparseMerkleTree {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl SparseMerkleTree {
    #[new]
    pub fn new() -> Self {
        // Precompute default hashes for empty nodes at each level (0 to 256)
        let mut default_hashes = Vec::with_capacity(257);
        let mut current_hash = [0u8; 32]; // Level 0 default is all zeros
        default_hashes.push(current_hash);

        for _ in 0..256 {
            let mut hasher = Sha256::new();
            hasher.update(current_hash);
            hasher.update(current_hash);
            let next_hash: [u8; 32] = hasher.finalize().into();
            default_hashes.push(next_hash);
            current_hash = next_hash;
        }

        SparseMerkleTree {
            leaves: HashMap::new(),
            default_hashes,
            tree_nodes: HashMap::new(),
        }
    }

    pub fn insert(&mut self, path_hex: &str, value_hex: &str) -> PyResult<String> {
        let path = path_hex.to_string();
        let value = value_hex.to_string();
        self.leaves.insert(path.clone(), value.clone());

        // Parse hex path to bit vector (represented as a String of '0' and '1')
        let path_bytes = hex::decode(&path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid hex path: {}", e))
        })?;
        if path_bytes.len() != 32 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Path must be a 32-byte hex string (256 bits)",
            ));
        }

        let bit_path = bytes_to_bits(&path_bytes);

        // Compute leaf hash
        let value_bytes = hex::decode(&value).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid hex value: {}", e))
        })?;
        let mut hasher = Sha256::new();
        hasher.update(&value_bytes);
        let mut current_hash: [u8; 32] = hasher.finalize().into();

        // Update nodes going up to the root
        let mut prefix = bit_path.clone();
        for level in 0..256 {
            self.tree_nodes.insert(prefix.clone(), current_hash);
            
            if prefix.is_empty() {
                break;
            }

            let last_bit = prefix.pop().unwrap();
            let sibling_prefix = format!("{}{}", prefix, if last_bit == '0' { '1' } else { '0' });

            let sibling_hash = self
                .tree_nodes
                .get(&sibling_prefix)
                .copied()
                .unwrap_or(self.default_hashes[level]);

            let mut parent_hasher = Sha256::new();
            if last_bit == '0' {
                parent_hasher.update(current_hash);
                parent_hasher.update(sibling_hash);
            } else {
                parent_hasher.update(sibling_hash);
                parent_hasher.update(current_hash);
            }
            current_hash = parent_hasher.finalize().into();
        }

        // Store the final root node (empty prefix)
        self.tree_nodes.insert("".to_string(), current_hash);

        Ok(hex::encode(current_hash))
    }

    pub fn get_root_hash(&self) -> String {
        let root_hash = self
            .tree_nodes
            .get("")
            .copied()
            .unwrap_or(self.default_hashes[256]);
        hex::encode(root_hash)
    }

    pub fn generate_proof(&self, path_hex: &str) -> PyResult<Vec<String>> {
        let path = path_hex.to_string();
        let path_bytes = hex::decode(&path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid hex path: {}", e))
        })?;
        if path_bytes.len() != 32 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Path must be a 32-byte hex string (256 bits)",
            ));
        }

        let bit_path = bytes_to_bits(&path_bytes);
        let mut proof = Vec::with_capacity(256);
        let mut prefix = bit_path;

        for level in 0..256 {
            if prefix.is_empty() {
                break;
            }
            let last_bit = prefix.pop().unwrap();
            let sibling_prefix = format!("{}{}", prefix, if last_bit == '0' { '1' } else { '0' });

            let sibling_hash = self
                .tree_nodes
                .get(&sibling_prefix)
                .copied()
                .unwrap_or(self.default_hashes[level]);

            proof.push(hex::encode(sibling_hash));
        }

        Ok(proof)
    }

    pub fn verify_proof(&self, root_hex: &str, path_hex: &str, value_hex: &str, proof: Vec<String>) -> PyResult<bool> {
        if proof.len() != 256 {
            return Ok(false);
        }

        let path_bytes = hex::decode(path_hex).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid hex path: {}", e))
        })?;
        let value_bytes = hex::decode(value_hex).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid hex value: {}", e))
        })?;
        
        let bit_path = bytes_to_bits(&path_bytes);
        let mut hasher = Sha256::new();
        hasher.update(&value_bytes);
        let mut current_hash: [u8; 32] = hasher.finalize().into();

        let mut bits = bit_path;
        for level in 0..256 {
            let last_bit = bits.pop().unwrap();
            let sibling_hash_bytes = hex::decode(&proof[level]).map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid proof hash: {}", e))
            })?;
            let mut sibling_hash = [0u8; 32];
            sibling_hash.copy_from_slice(&sibling_hash_bytes);

            let mut parent_hasher = Sha256::new();
            if last_bit == '0' {
                parent_hasher.update(current_hash);
                parent_hasher.update(sibling_hash);
            } else {
                parent_hasher.update(sibling_hash);
                parent_hasher.update(current_hash);
            }
            current_hash = parent_hasher.finalize().into();
        }

        Ok(hex::encode(current_hash) == root_hex)
    }
}

fn bytes_to_bits(bytes: &[u8]) -> String {
    let mut bits = String::with_capacity(bytes.len() * 8);
    for &byte in bytes {
        for i in (0..8).rev() {
            bits.push(if (byte & (1 << i)) != 0 { '1' } else { '0' });
        }
    }
    bits
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_smt_lifecycle() {
        let mut smt = SparseMerkleTree::new();
        let key = hex::encode(Sha256::digest(b"test_key"));
        let value = hex::encode(Sha256::digest(b"test_value"));

        let root = smt.insert(&key, &value).unwrap();
        assert_eq!(root, smt.get_root_hash());

        let proof = smt.generate_proof(&key).unwrap();
        assert_eq!(proof.len(), 256);

        let verified = smt.verify_proof(&root, &key, &value, proof).unwrap();
        assert!(verified);
    }
}
