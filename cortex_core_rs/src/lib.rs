pub mod ast;
pub mod merkle;
pub mod logger;

use pyo3::prelude::*;

#[pymodule]
fn cortex_core_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(ast::hash_ast, m)?)?;
    m.add_function(wrap_pyfunction!(ast::generate_evidence_hash, m)?)?;
    m.add_function(wrap_pyfunction!(merkle::batch_merkle_root, m)?)?;
    m.add_function(wrap_pyfunction!(logger::log_ast_check, m)?)?;
    Ok(())
}
