use pyo3::prelude::*;
use wasm_runtime::swarm::WasmSwarm;

#[pyclass]
pub struct PyWasmSwarm {
    inner: WasmSwarm,
}

#[pymethods]
impl PyWasmSwarm {
    #[new]
    pub fn new() -> Self {
        Self {
            inner: WasmSwarm::new(),
        }
    }

    pub fn spawn_agent(&mut self, agent_id: String, wasm_bytes: &[u8]) -> PyResult<()> {
        self.inner.spawn_agent(agent_id, wasm_bytes).map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!("Error instantiating WASM: {}", e))
        })
    }

    pub fn kill_agent(&mut self, agent_id: &str) {
        self.inner.kill_agent(agent_id);
    }

    pub fn cycle_friction(&self, agent_id: &str, friction_signal: f64) -> PyResult<f64> {
        self.inner.cycle_friction(agent_id, friction_signal).map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!("Error cycling WASM friction: {}", e))
        })
    }

    pub fn active_count(&self) -> usize {
        self.inner.active_count()
    }
}
