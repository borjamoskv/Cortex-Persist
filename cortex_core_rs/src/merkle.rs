use pyo3::prelude::*;
use sha3::{Digest, Sha3_256};

#[pyfunction]
pub fn batch_merkle_root(hashes: Vec<String>) -> PyResult<String> {
    if hashes.is_empty() {
        return Ok(String::new());
    }

    let mut current_level = hashes;

    while current_level.len() > 1 {
        let mut next_level = Vec::new();
        
        for chunk in current_level.chunks(2) {
            let mut hasher = Sha3_256::new();
            if chunk.len() == 2 {
                hasher.update(chunk[0].as_bytes());
                hasher.update(chunk[1].as_bytes());
            } else {
                // If odd number of hashes, duplicate the last one
                hasher.update(chunk[0].as_bytes());
                hasher.update(chunk[0].as_bytes());
            }
            next_level.push(hex::encode(hasher.finalize()));
        }
        current_level = next_level;
    }

    Ok(current_level[0].clone())
}
