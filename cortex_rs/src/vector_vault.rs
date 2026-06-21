use aes_gcm::{
    aead::{rand_core::RngCore, Aead, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use anyhow::Result;
use rand::{SeedableRng, RngExt};
use rand::rngs::StdRng;

pub struct VectorVault {
    cipher: Aes256Gcm,
    pub q_matrix: Vec<f32>,
    pub dimension: usize,
}

#[derive(Debug, Clone)]
pub struct EncryptedVector {
    pub ciphertext: Vec<u8>,
    pub nonce: [u8; 12],
    pub dimension: usize,
}

impl VectorVault {
    pub fn new(key: &[u8; 32], dimension: usize) -> Self {
        let cipher = Aes256Gcm::new_from_slice(key).expect("Key must be 32 bytes");
        let q_matrix = generate_orthogonal_matrix(key, dimension);
        Self {
            cipher,
            q_matrix,
            dimension,
        }
    }

    pub fn generate_key() -> [u8; 32] {
        let mut key = [0u8; 32];
        OsRng.fill_bytes(&mut key);
        key
    }

    pub fn encrypt(&self, embedding: &[f32]) -> Result<EncryptedVector> {
        assert_eq!(embedding.len(), self.dimension, "Embedding dimension mismatch");

        // 1. Orthogonally obfuscate: v' = Q * v
        let obf_embedding = mat_vec_mul(&self.q_matrix, embedding, self.dimension);

        let mut nonce_bytes = [0u8; 12];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);

        let plaintext: Vec<u8> = obf_embedding.iter().flat_map(|f| f.to_le_bytes()).collect();

        let ciphertext = self
            .cipher
            .encrypt(nonce, plaintext.as_ref())
            .map_err(|e| anyhow::anyhow!("Encryption failed: {}", e))?;

        Ok(EncryptedVector {
            ciphertext,
            nonce: nonce_bytes,
            dimension: self.dimension,
        })
    }

    pub fn decrypt(&self, encrypted: &EncryptedVector) -> Result<Vec<f32>> {
        assert_eq!(encrypted.dimension, self.dimension, "Encrypted vector dimension mismatch");

        let nonce = Nonce::from_slice(&encrypted.nonce);

        let plaintext = self
            .cipher
            .decrypt(nonce, encrypted.ciphertext.as_ref())
            .map_err(|e| anyhow::anyhow!("Decryption failed: {}", e))?;

        let obf_embedding: Vec<f32> = plaintext
            .chunks_exact(4)
            .map(|chunk| {
                let bytes: [u8; 4] = chunk.try_into().unwrap();
                f32::from_le_bytes(bytes)
            })
            .collect();

        assert_eq!(obf_embedding.len(), self.dimension);

        // 2. De-obfuscate: v = Q^T * v'
        let embedding = mat_transpose_vec_mul(&self.q_matrix, &obf_embedding, self.dimension);
        Ok(embedding)
    }

    /// Búsqueda sobre vectores cifrados.
    /// Descifra en memoria, calcula coseno, destruye el plaintext (obfuscated vector).
    pub fn search_encrypted(
        &self,
        query: &[f32],
        encrypted_vectors: &[EncryptedVector],
        top_k: usize,
        threshold: f32,
    ) -> Result<Vec<(usize, f32)>> {
        assert_eq!(query.len(), self.dimension, "Query dimension mismatch");

        // 1. Obfuscate query vector: q' = Q * q
        let obf_query = mat_vec_mul(&self.q_matrix, query, self.dimension);

        let mut results: Vec<(usize, f32)> = encrypted_vectors
            .iter()
            .enumerate()
            .filter_map(|(idx, enc)| {
                if enc.dimension != self.dimension {
                    return None;
                }
                
                // Decrypt stored vector, yielding the obfuscated vector in RAM
                let nonce = Nonce::from_slice(&enc.nonce);
                let plaintext = self
                    .cipher
                    .decrypt(nonce, enc.ciphertext.as_ref())
                    .ok()?;
                
                let obf_embedding: Vec<f32> = plaintext
                    .chunks_exact(4)
                    .map(|chunk| {
                        let bytes: [u8; 4] = chunk.try_into().unwrap();
                        f32::from_le_bytes(bytes)
                    })
                    .collect();

                // Compute cosine similarity between the obfuscated representations directly in RAM
                let sim = cosine_simd(&obf_query, &obf_embedding);
                
                if sim >= threshold {
                    Some((idx, sim))
                } else {
                    None
                }
            })
            .collect();

        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        results.truncate(top_k);
        Ok(results)
    }
}

pub fn cosine_simd(a: &[f32], b: &[f32]) -> f32 {
    a.iter().zip(b).map(|(x, y)| x * y).sum()
}

fn generate_orthogonal_matrix(key: &[u8; 32], dim: usize) -> Vec<f32> {
    let mut rng = StdRng::from_seed(*key);
    
    // Box-Muller transform helper to sample standard normal distribution in f64
    let standard_normal = |rng: &mut StdRng| -> f64 {
        let u1: f64 = rng.random();
        let u2: f64 = rng.random();
        let ln_u1: f64 = u1.ln();
        let cos_u2: f64 = (2.0f64 * std::f64::consts::PI * u2).cos();
        (-2.0f64 * ln_u1).sqrt() * cos_u2
    };

    // 1. Generate Random Gaussian Matrix (dim x dim) in f64
    let mut a = vec![0.0f64; dim * dim];
    for val in a.iter_mut() {
        *val = standard_normal(&mut rng);
    }

    // 2. Modified Gram-Schmidt Orthogonalization (columns of A) in f64
    let mut q = vec![0.0f64; dim * dim];
    
    for i in 0..dim {
        // Copy column i of A to V
        let mut v = vec![0.0f64; dim];
        for r in 0..dim {
            v[r] = a[r * dim + i];
        }
        
        for j in 0..i {
            // Project v onto q_j (column j of Q)
            let mut dot = 0.0f64;
            for r in 0..dim {
                dot += v[r] * q[r * dim + j];
            }
            
            // Subtract projection
            for r in 0..dim {
                v[r] -= dot * q[r * dim + j];
            }
        }
        
        // Normalize
        let mut norm = 0.0f64;
        for r in 0..dim {
            norm += v[r] * v[r];
        }
        norm = norm.sqrt();
        
        if norm > 1e-15 {
            for r in 0..dim {
                q[r * dim + i] = v[r] / norm;
            }
        } else {
            // Fallback if linearly dependent
            for r in 0..dim {
                q[r * dim + i] = if r == i { 1.0 } else { 0.0 };
            }
        }
    }
    
    // Cast to f32 for storage and performance
    q.into_iter().map(|x| x as f32).collect()
}

fn mat_vec_mul(q: &[f32], v: &[f32], dim: usize) -> Vec<f32> {
    let mut out = vec![0.0; dim];
    for r in 0..dim {
        let mut sum = 0.0;
        let row_offset = r * dim;
        for c in 0..dim {
            sum += q[row_offset + c] * v[c];
        }
        out[r] = sum;
    }
    out
}

fn mat_transpose_vec_mul(q: &[f32], y: &[f32], dim: usize) -> Vec<f32> {
    let mut out = vec![0.0; dim];
    for c in 0..dim {
        let mut sum = 0.0;
        for r in 0..dim {
            sum += q[r * dim + c] * y[r];
        }
        out[c] = sum;
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encrypt_decrypt_roundtrip() {
        let key = VectorVault::generate_key();
        let dim = 5;
        let vault = VectorVault::new(&key, dim);
        let original = vec![0.1, 0.2, 0.3, 0.4, 0.5];

        let encrypted = vault.encrypt(&original).unwrap();
        let decrypted = vault.decrypt(&encrypted).unwrap();

        for (a, b) in original.iter().zip(decrypted.iter()) {
            assert!((a - b).abs() < 1e-6, "Roundtrip debe ser exacto (dentro de tolerancia numérica)");
        }
    }

    #[test]
    fn test_wrong_key_fails() {
        let key1 = VectorVault::generate_key();
        let key2 = VectorVault::generate_key();
        let dim = 3;
        let vault1 = VectorVault::new(&key1, dim);
        let vault2 = VectorVault::new(&key2, dim);

        let original = vec![0.1, 0.2, 0.3];
        let encrypted = vault1.encrypt(&original).unwrap();

        assert!(
            vault2.decrypt(&encrypted).is_err(),
            "Clave incorrecta debe fallar"
        );
    }

    #[test]
    fn test_tampered_ciphertext_fails() {
        let key = VectorVault::generate_key();
        let dim = 3;
        let vault = VectorVault::new(&key, dim);
        let original = vec![0.1, 0.2, 0.3];

        let mut encrypted = vault.encrypt(&original).unwrap();
        // Modificar un byte
        if let Some(byte) = encrypted.ciphertext.get_mut(0) {
            *byte ^= 0xFF;
        }

        assert!(
            vault.decrypt(&encrypted).is_err(),
            "Ciphertext modificado debe fallar (AEAD tag)"
        );
    }

    #[test]
    fn test_obfuscation_preserves_cosine() {
        let key = VectorVault::generate_key();
        let dim = 384;
        let vault = VectorVault::new(&key, dim);

        // Check if Q^T Q = I
        for i in 0..5 { // Check first 5 columns for simplicity and speed
            for j in 0..5 {
                let mut sum = 0.0;
                for r in 0..dim {
                    sum += vault.q_matrix[r * dim + i] * vault.q_matrix[r * dim + j];
                }
                if i == j {
                    assert!((sum - 1.0).abs() < 1e-3, "Diagonal Q^T Q element {},{} is {}, not 1.0", i, j, sum);
                } else {
                    assert!(sum.abs() < 1e-3, "Off-diagonal Q^T Q element {},{} is {}, not 0.0", i, j, sum);
                }
            }
        }

        // Generate two vectors
        let v1: Vec<f32> = (0..dim).map(|i| (i as f32).sin()).collect();
        let v2: Vec<f32> = (0..dim).map(|i| (i as f32).cos()).collect();

        // Calculate original cosine similarity
        let dot_original = cosine_simd(&v1, &v2);

        // Obfuscate them
        let ov1 = mat_vec_mul(&vault.q_matrix, &v1, dim);
        let ov2 = mat_vec_mul(&vault.q_matrix, &v2, dim);

        // Calculate obfuscated cosine similarity
        let dot_obfuscated = cosine_simd(&ov1, &ov2);

        let diff = (dot_original - dot_obfuscated).abs();
        assert!(diff < 1e-3, "Cosine/dot-product must be preserved by orthogonal obfuscation: original = {}, obfuscated = {}, diff = {}", dot_original, dot_obfuscated, diff);
    }
}

