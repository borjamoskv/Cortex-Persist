use aes_gcm::{
    aead::{rand_core::RngCore, Aead, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use anyhow::Result;

pub struct VectorVault {
    cipher: Aes256Gcm,
}

#[derive(Debug, Clone)]
pub struct EncryptedVector {
    pub ciphertext: Vec<u8>,
    pub nonce: [u8; 12],
    pub dimension: usize,
}

impl VectorVault {
    pub fn new(key: &[u8; 32]) -> Self {
        let cipher = Aes256Gcm::new_from_slice(key).expect("Key must be 32 bytes");
        Self { cipher }
    }

    pub fn generate_key() -> [u8; 32] {
        let mut key = [0u8; 32];
        OsRng.fill_bytes(&mut key);
        key
    }

    pub fn encrypt(&self, embedding: &[f32]) -> Result<EncryptedVector> {
        let mut nonce_bytes = [0u8; 12];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);

        let plaintext: Vec<u8> = embedding.iter().flat_map(|f| f.to_le_bytes()).collect();

        let ciphertext = self
            .cipher
            .encrypt(nonce, plaintext.as_ref())
            .map_err(|e| anyhow::anyhow!("Encryption failed: {}", e))?;

        Ok(EncryptedVector {
            ciphertext,
            nonce: nonce_bytes,
            dimension: embedding.len(),
        })
    }

    pub fn decrypt(&self, encrypted: &EncryptedVector) -> Result<Vec<f32>> {
        let nonce = Nonce::from_slice(&encrypted.nonce);

        let plaintext = self
            .cipher
            .decrypt(nonce, encrypted.ciphertext.as_ref())
            .map_err(|e| anyhow::anyhow!("Decryption failed: {}", e))?;

        let embedding: Vec<f32> = plaintext
            .chunks_exact(4)
            .map(|chunk| {
                let bytes: [u8; 4] = chunk.try_into().unwrap();
                f32::from_le_bytes(bytes)
            })
            .collect();

        assert_eq!(embedding.len(), encrypted.dimension);
        Ok(embedding)
    }

    /// Búsqueda sobre vectores cifrados.
    /// Descifra en memoria, calcula coseno, destruye el plaintext.
    pub fn search_encrypted(
        &self,
        query: &[f32],
        encrypted_vectors: &[EncryptedVector],
        top_k: usize,
        threshold: f32,
    ) -> Result<Vec<(usize, f32)>> {
        let mut results: Vec<(usize, f32)> = encrypted_vectors
            .iter()
            .enumerate()
            .filter_map(|(idx, enc)| {
                let decrypted = self.decrypt(enc).ok()?;
                let sim = cosine_simd(query, &decrypted);
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encrypt_decrypt_roundtrip() {
        let key = VectorVault::generate_key();
        let vault = VectorVault::new(&key);
        let original = vec![0.1, 0.2, 0.3, 0.4, 0.5];

        let encrypted = vault.encrypt(&original).unwrap();
        let decrypted = vault.decrypt(&encrypted).unwrap();

        for (a, b) in original.iter().zip(decrypted.iter()) {
            assert!((a - b).abs() < 1e-7, "Roundtrip debe ser exacto");
        }
    }

    #[test]
    fn test_wrong_key_fails() {
        let key1 = VectorVault::generate_key();
        let key2 = VectorVault::generate_key();
        let vault1 = VectorVault::new(&key1);
        let vault2 = VectorVault::new(&key2);

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
        let vault = VectorVault::new(&key);
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
}
