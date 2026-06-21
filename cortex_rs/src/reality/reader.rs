use serde_json::Value;
use std::fs::File;
use std::io::{BufRead, BufReader};
use pyo3::prelude::*;

#[pyfunction]
pub fn load_verified_reality(ledger_path: &str) -> PyResult<Vec<String>> {
    let file = File::open(ledger_path).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    let reader = BufReader::new(file);
    let mut claims = Vec::new();

    for line in reader.lines() {
        if let Ok(l) = line {
            if let Ok(parsed) = serde_json::from_str::<Value>(&l) {
                if let Some(status) = parsed.get("status").and_then(|s| s.as_str()) {
                    if status == "verified" {
                        let score = parsed.get("trust_score").and_then(|s| s.as_f64()).unwrap_or(0.0);
                        claims.push((score, l));
                    }
                }
            }
        }
    }
    
    // Orden descendente por trust_score
    claims.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
    Ok(claims.into_iter().map(|(_, l)| l).collect())
}
