use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use cortex_rs::{submit_ir, get_ledger_root};
use cortex_chaos::parse_ir;
use cortex_rs::{CortexKernel, KernelTrait};

/// Submit an Intermediate Representation (IR) to the determinist kernel
#[pyfunction]
fn submit_ir_py(py: Python<'_>, ir: String) -> PyResult<String> {
    py.allow_threads(|| {
        match submit_ir(&ir) {
            Ok(hash) => Ok(hash),
            Err(e) => Err(PyValueError::new_err(e)),
        }
    })
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

#[derive(Clone, Debug)]
pub struct BoundaryKernel {
    inner: CortexKernel,
}

impl BoundaryKernel {
    pub fn new() -> Self {
        Self {
            inner: CortexKernel::new(),
        }
    }

    pub fn submit_ir(&mut self, ir: &str) -> String {
        let event = parse_ir(ir).unwrap_or(cortex_types::Event::Unknown(ir.to_string()));
        match self.inner.apply_event(event) {
            cortex_types::KernelResult::Accepted => "ACCEPTED".to_string(),
            cortex_types::KernelResult::Rejected => "REJECTED".to_string(),
            cortex_types::KernelResult::Collapse { reason } => format!("HARD_FAIL:{:?}", reason),
        }
    }

    pub fn state_hash(&self) -> String {
        cortex_types::hex32(&self.inner.state_hash())
    }

    pub fn ledger_root(&self) -> String {
        cortex_types::hex32(&self.inner.ledger_root())
    }
}
