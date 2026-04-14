//! cortex_rs — High-performance cryptographic primitives for CORTEX Persist.
//!
//! Exposes a Python module (`cortex_rs`) via PyO3 with:
//!   - SHA-256 hashing and hash-chaining (releases the GIL).
//!   - Merkle-tree root computation over a list of hex-encoded leaf hashes.
//!   - Batch Ed25519 signature verification (releases the GIL).
//!
//! Python fallback: all callers guard against `ImportError` and fall back to
//! `hashlib` / `cryptography` when this native module is not installed.

#[cfg(feature = "extension-module")]
use pyo3::prelude::*;

use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use hex;
use sha2::{Digest, Sha256};

// ─── Internal helpers (used by both the Python module and any Rust unit tests) ─

/// Compute the SHA-256 hex digest of an arbitrary byte slice.
fn _sha256_bytes(data: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(data);
    hex::encode(h.finalize())
}

/// Hash-pair combiner: SHA-256(left_hex_str + right_hex_str).
///
/// Matches `MerkleTree._hash_pair` and `compute_merkle_root` in the Python layer.
fn _hash_pair(left: &str, right: &str) -> String {
    let mut h = Sha256::new();
    h.update(left.as_bytes());
    h.update(right.as_bytes());
    hex::encode(h.finalize())
}

/// Compute the Merkle root of a list of hex-encoded leaf hashes.
///
/// Follows the same algorithm as `cortex.consensus.merkle.compute_merkle_root`:
///   - Odd-length levels duplicate the last element.
///   - Returns `None` for an empty input.
fn _merkle_root_inner(mut level: Vec<String>) -> Option<String> {
    if level.is_empty() {
        return None;
    }
    while level.len() > 1 {
        let mut next: Vec<String> = Vec::with_capacity((level.len() + 1) / 2);
        let mut i = 0;
        while i < level.len() {
            let left = &level[i];
            let right = if i + 1 < level.len() { &level[i + 1] } else { left };
            next.push(_hash_pair(left, right));
            i += 2;
        }
        level = next;
    }
    level.into_iter().next()
}

// ─── PyO3 Python bindings ──────────────────────────────────────────────────

#[cfg(feature = "extension-module")]
#[pyfunction]
/// Compute the SHA-256 hex digest of a UTF-8 string.
///
/// Equivalent to ``hashlib.sha256(data.encode()).hexdigest()``.
fn sha256_hash(data: &str) -> String {
    _sha256_bytes(data.as_bytes())
}

#[cfg(feature = "extension-module")]
#[pyfunction]
/// Chain-hash: SHA-256 of ``prev_hash + '\x00' + data`` (null-byte separated).
///
/// Matches the null-byte canonical form used in ``compute_tx_hash`` so that
/// Rust and Python produce identical digests.
fn sha256_chain_hash(prev_hash: &str, data: &str) -> String {
    let mut h = Sha256::new();
    h.update(prev_hash.as_bytes());
    h.update(b"\x00");
    h.update(data.as_bytes());
    hex::encode(h.finalize())
}

#[cfg(feature = "extension-module")]
#[pyfunction]
/// Compute the Merkle root over a list of hex-encoded leaf hashes.
///
/// Returns ``None`` for an empty list, otherwise the hex root hash.
/// Odd-length levels duplicate the last leaf (matches the Python implementation).
fn merkle_root(hashes: Vec<String>) -> Option<String> {
    _merkle_root_inner(hashes)
}

#[cfg(feature = "extension-module")]
#[pyfunction]
/// Batch-verify Ed25519 signatures, releasing the GIL for the entire batch.
///
/// Args:
///     messages:    List of raw message bytes.
///     public_keys: List of 32-byte raw Ed25519 public keys.
///     signatures:  List of 64-byte raw Ed25519 signatures.
///
/// Returns:
///     A list of booleans — ``True`` when the corresponding signature is valid.
///
/// Raises:
///     ValueError: When the three lists have different lengths.
fn verify_ed25519_batch(
    py: Python<'_>,
    messages: Vec<Vec<u8>>,
    public_keys: Vec<Vec<u8>>,
    signatures: Vec<Vec<u8>>,
) -> PyResult<Vec<bool>> {
    if messages.len() != public_keys.len() || messages.len() != signatures.len() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "messages, public_keys, and signatures must have the same length",
        ));
    }

    // Release the GIL for the CPU-intensive verification loop.
    let results = py.allow_threads(|| {
        messages
            .iter()
            .zip(public_keys.iter())
            .zip(signatures.iter())
            .map(|((msg, pk_bytes), sig_bytes)| {
                let Ok(pk_arr): Result<[u8; 32], _> = pk_bytes.as_slice().try_into() else {
                    return false;
                };
                let Ok(sig_arr): Result<[u8; 64], _> = sig_bytes.as_slice().try_into() else {
                    return false;
                };
                let Ok(vk) = VerifyingKey::from_bytes(&pk_arr) else {
                    return false;
                };
                let sig = Signature::from_bytes(&sig_arr);
                vk.verify(msg, &sig).is_ok()
            })
            .collect::<Vec<bool>>()
    });

    Ok(results)
}

#[cfg(feature = "extension-module")]
#[pymodule]
/// cortex_rs — Rust-accelerated cryptographic primitives for CORTEX Persist.
fn cortex_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sha256_hash, m)?)?;
    m.add_function(wrap_pyfunction!(sha256_chain_hash, m)?)?;
    m.add_function(wrap_pyfunction!(merkle_root, m)?)?;
    m.add_function(wrap_pyfunction!(verify_ed25519_batch, m)?)?;
    Ok(())
}

// ─── Unit tests (pure Rust, no Python) ────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sha256_bytes_known_value() {
        // SHA-256("") == e3b0c44298fc1c149afb...
        let result = _sha256_bytes(b"");
        assert!(result.starts_with("e3b0c44298fc1c14"));
    }

    #[test]
    fn test_merkle_root_single() {
        let h = "abc".to_string();
        assert_eq!(_merkle_root_inner(vec![h.clone()]), Some(h));
    }

    #[test]
    fn test_merkle_root_two_leaves() {
        let a = "aa".to_string();
        let b = "bb".to_string();
        let expected = _hash_pair(&a, &b);
        assert_eq!(_merkle_root_inner(vec![a, b]), Some(expected));
    }

    #[test]
    fn test_merkle_root_empty() {
        assert_eq!(_merkle_root_inner(vec![]), None);
    }

    #[test]
    fn test_ed25519_valid_signature() {
        use ed25519_dalek::{Signer, SigningKey};
        let sk = SigningKey::generate(&mut rand_core::OsRng);
        let vk = sk.verifying_key();
        let msg = b"cortex test message";
        let sig = sk.sign(msg);

        let results = messages_zip_verify(
            vec![msg.to_vec()],
            vec![vk.to_bytes().to_vec()],
            vec![sig.to_bytes().to_vec()],
        );
        assert_eq!(results, vec![true]);
    }

    #[test]
    fn test_ed25519_invalid_signature() {
        // Generate a real key pair but sign a different message, so verification fails.
        use ed25519_dalek::{Signer, SigningKey};
        let sk = SigningKey::generate(&mut rand_core::OsRng);
        let vk = sk.verifying_key();
        let original_msg = b"correct message";
        let sig = sk.sign(original_msg);
        // Pass a *different* message — the signature should not verify.
        let results = messages_zip_verify(
            vec![b"wrong message".to_vec()],
            vec![vk.to_bytes().to_vec()],
            vec![sig.to_bytes().to_vec()],
        );
        assert_eq!(results, vec![false]);
    }

    // Helper to call the inner verification logic without needing a Python runtime.
    fn messages_zip_verify(
        messages: Vec<Vec<u8>>,
        public_keys: Vec<Vec<u8>>,
        signatures: Vec<Vec<u8>>,
    ) -> Vec<bool> {
        messages
            .iter()
            .zip(public_keys.iter())
            .zip(signatures.iter())
            .map(|((msg, pk_bytes), sig_bytes)| {
                let Ok(pk_arr): Result<[u8; 32], _> = pk_bytes.as_slice().try_into() else {
                    return false;
                };
                let Ok(sig_arr): Result<[u8; 64], _> = sig_bytes.as_slice().try_into() else {
                    return false;
                };
                let Ok(vk) = VerifyingKey::from_bytes(&pk_arr) else {
                    return false;
                };
                let sig = Signature::from_bytes(&sig_arr);
                vk.verify(msg, &sig).is_ok()
            })
            .collect()
    }
}
