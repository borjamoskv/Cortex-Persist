pub mod heuristics;
pub mod audit;
pub mod engine;

use pyo3::prelude::*;
use audit::AuditTrail;
use engine::RewriteEngine;

#[pymodule]
fn cortex_merkle_rewrite(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<AuditTrail>()?;
    m.add_class::<RewriteEngine>()?;
    Ok(())
}
