use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SmtLeaf {
    #[pyo3(get, set)]
    pub path: String,
    #[pyo3(get, set)]
    pub value_hash: String,
}

#[pymethods]
impl SmtLeaf {
    #[new]
    pub fn new(path: String, value_hash: String) -> Self {
        SmtLeaf { path, value_hash }
    }
}
