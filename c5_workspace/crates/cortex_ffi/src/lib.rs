use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use cortex_rs::{submit_ir, get_ledger_root};

/// Submit an Intermediate Representation (IR) to the determinist kernel
#[pyfunction]
fn submit_ir_py(ir: String) -> PyResult<String> {
    match submit_ir(&ir) {
        Ok(hash) => Ok(hash),
        Err(e) => Err(PyValueError::new_err(e)),
    }
}

/// Retrieve the current ledger root hash
#[pyfunction]
fn get_ledger_root_py() -> PyResult<String> {
    match get_ledger_root() {
        Ok(root) => Ok(root),
        Err(e) => Err(PyValueError::new_err(e)),
    }
}

/// Cortex C5-REAL FFI Module
#[pymodule]
fn cortex_ffi(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(submit_ir_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_ledger_root_py, m)?)?;
    Ok(())
}
