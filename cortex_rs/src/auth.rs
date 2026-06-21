use argon2::{Argon2, Algorithm, Version, Params, PasswordHash, PasswordHasher, PasswordVerifier};
use argon2::password_hash::{rand_core::OsRng, SaltString};
use pyo3::prelude::*;

#[pyfunction]
pub fn hash_password(password: &str) -> PyResult<String> {
    let salt = SaltString::generate(&mut OsRng);
    // Use the exact same parameters as cortex/auth/manager.py:
    // m_cost = 65536, t_cost = 2, p_cost = 1, output length = 32
    let params = Params::new(65536, 2, 1, Some(32))
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid Argon2 params: {}", e)))?;
    let argon2 = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);

    let hash = argon2.hash_password(password.as_bytes(), &salt)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Hashing failed: {}", e)))?;

    Ok(hash.to_string())
}

#[pyfunction]
pub fn verify_password(password: &str, hash: &str) -> PyResult<bool> {
    let parsed = PasswordHash::new(hash)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid password hash format: {}", e)))?;

    // Use custom params parser to verify with correct argon2id parameters
    let params = Params::new(65536, 2, 1, Some(32))
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid Argon2 params: {}", e)))?;
    let argon2 = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);

    Ok(argon2.verify_password(password.as_bytes(), &parsed).is_ok())
}
