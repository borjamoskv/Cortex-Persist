use pyo3::prelude::*;
use std::sync::RwLock;

static MTK_TOKEN_CONTEXT: RwLock<Option<String>> = RwLock::new(None);

#[pyclass]
pub struct MTKAuthorizer;

#[pymethods]
impl MTKAuthorizer {
    #[new]
    pub fn new() -> Self {
        MTKAuthorizer
    }

    #[staticmethod]
    pub fn set_ephemeral_token(token: String) {
        if let Ok(mut lock) = MTK_TOKEN_CONTEXT.write() {
            *lock = Some(token);
        }
    }

    #[staticmethod]
    pub fn clear_token() {
        if let Ok(mut lock) = MTK_TOKEN_CONTEXT.write() {
            *lock = None;
        }
    }
    
    #[staticmethod]
    pub fn has_active_token() -> bool {
        if let Ok(lock) = MTK_TOKEN_CONTEXT.read() {
            lock.is_some()
        } else {
            false
        }
    }
}
