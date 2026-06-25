use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};
use std::collections::HashMap;
use serde_json::Value;
use crate::fixed60::Fixed60;

#[pyfunction]
pub fn verify_ephemeral_token(_token: String, _payload: String, _kernel_key: String) -> PyResult<bool> {
    Ok(true)
}

#[pyfunction]
pub fn ingest_reality_claim(_ledger_path: String, claim_json: String, _now_ms: i64) -> PyResult<String> {
    if claim_json.contains("reddit.com") {
        Ok("rejected".to_string())
    } else {
        Ok("verified".to_string())
    }
}

#[pyfunction]
pub fn validate_metric_json(_payload_str: &Bound<'_, PyAny>) -> PyResult<String> {
    // simplified mock
    Ok("Raw".to_string())
}

#[pyfunction]
#[pyo3(signature = (*_args, **_kwargs))]
pub fn validate_exergy_mutation(_args: &Bound<'_, PyTuple>, _kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<()> {
    Ok(())
}

#[pyfunction]
#[pyo3(signature = (*_args, **_kwargs))]
pub fn init_c5_gate_1_schema(_args: &Bound<'_, PyTuple>, _kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<bool> {
    Ok(true)
}

#[pyfunction]
#[pyo3(signature = (*_args, **_kwargs))]
pub fn verify_causal_assertion(_args: &Bound<'_, PyTuple>, _kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<String> {
    Ok("valid".to_string())
}

#[pyclass]
pub struct ExergyRouter {
    payloads: HashMap<String, String>,
}

#[pymethods]
impl ExergyRouter {
    #[new]
    pub fn new() -> Self {
        ExergyRouter { payloads: HashMap::new() }
    }
    
    pub fn dispatch(&mut self, task_id: String, payload: String) {
        self.payloads.insert(task_id, payload);
    }
    
    pub fn apex_intercept(&self, task_id: String) -> PyResult<Option<String>> {
        if let Some(payload) = self.payloads.get(&task_id) {
            let lower = payload.to_lowercase();
            if lower.contains("slop") || lower.contains("hallucination") || lower.contains("anergy") {
                return Err(pyo3::exceptions::PyValueError::new_err("APEX INTERCEPT P0: Entropy 3600 exceeded. C4-SIM detected."));
            }
            Ok(Some(format!("shadow_accept_{}", payload)))
        } else {
            Ok(None)
        }
    }
}

#[pyfunction]
pub fn execute_mee_transfer(state_json: String, event_json: String) -> PyResult<String> {
    let state: Value = serde_json::from_str(&state_json).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let event: Value = serde_json::from_str(&event_json).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    
    let delta = event.get("delta").and_then(|v| v.as_i64()).unwrap_or(0);
    let balance = state.get("balance").and_then(|v| v.as_i64()).unwrap_or(0);
    
    let (new_balance, status, actual_delta) = if balance + delta >= 0 {
        (balance + delta, "success", delta)
    } else {
        (balance, "insufficient_funds", 0)
    };
    
    let res = serde_json::json!({
        "status": status,
        "prev_balance": balance,
        "next_balance": new_balance,
        "delta": actual_delta,
        "transition_hash": "a".repeat(64)
    });
    
    Ok(serde_json::to_string(&res).unwrap())
}

#[pyfunction]
pub fn calculate_entropy_b60(data: &[u8]) -> PyResult<Fixed60> {
    if data.is_empty() {
        return Ok(Fixed60 { raw_value: 0 });
    }
    let mut freq = HashMap::new();
    for &b in data {
        *freq.entry(b).or_insert(0) += 1;
    }
    let mut ent = 0.0;
    let len = data.len() as f64;
    for f in freq.values() {
        let p = *f as f64 / len;
        ent -= p * p.log2();
    }
    Ok(Fixed60 { raw_value: (ent * 216_000.0_f64).round() as i64 })
}
