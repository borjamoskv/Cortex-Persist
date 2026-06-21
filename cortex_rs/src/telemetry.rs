use chrono::{DateTime, Utc};
use crossbeam_channel::{unbounded, Receiver, Sender};
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::fs::OpenOptions;
use std::io::Write;
use std::thread;

/// The structural logging envelope per Cortex v2 spec.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CortexLogEnvelope {
    pub trace_id: String,
    pub span_id: String,
    pub ts: DateTime<Utc>,
    pub layer: String,
    pub event: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum EpistemicMetric {
    Raw(RawMetric),
    Derived(DerivedMetric),
    Narrative(NarrativeClaim),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "metric", rename_all = "snake_case")]
pub enum RawMetric {
    ExecutionDuration { path: String, duration_ms: u64 },
    GitDiffBytes { lines_added: u32, lines_removed: u32 },
    TokenConsumption { prompt_tokens: u32, completion_tokens: u32 },
    TestPassRate { total: u32, failed: u32 },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "formula", rename_all = "snake_case")]
pub enum DerivedMetric {
    ExergyRatio {
        raw_work_tokens: u32,
        total_tokens: u32,
        value: f64,
    },
    CausalDensity {
        edges: u32,
        nodes: u32,
        value: f64,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NarrativeClaim {
    pub label: String,
    pub description: String,
    pub evidence_roots: Vec<String>,
}

/// A lock-free, append-only, JSONL telemetry writer.
pub struct TelemetryEngine {
    sender: Sender<CortexLogEnvelope>,
}

impl TelemetryEngine {
    /// Creates a new TelemetryEngine that spawns a dedicated logging thread
    /// receiving events over an unbounded channel, ensuring the application
    /// threads are never blocked by I/O.
    pub fn new(log_path: &str) -> Self {
        let (sender, receiver): (Sender<CortexLogEnvelope>, Receiver<CortexLogEnvelope>) =
            unbounded();

        let file_path = log_path.to_string();
        thread::spawn(move || {
            let mut file = OpenOptions::new()
                .create(true)
                .append(true)
                .open(&file_path)
                .expect("Failed to open telemetry log file");

            while let Ok(envelope) = receiver.recv() {
                if let Ok(json) = serde_json::to_string(&envelope) {
                    // Append-only JSONL write
                    let _ = writeln!(file, "{}", json);
                }
            }
        });

        Self { sender }
    }

    /// Emits a self-contained telemetry event.
    pub fn emit(&self, trace_id: String, span_id: String, layer: String, event: serde_json::Value) {
        let envelope = CortexLogEnvelope {
            trace_id,
            span_id,
            ts: Utc::now(),
            layer,
            event,
        };
        // Fire and forget (lock-free)
        let _ = self.sender.send(envelope);
    }
}

#[pyfunction]
pub fn validate_metric_json(json_str: &str) -> PyResult<bool> {
    let _val: EpistemicMetric = serde_json::from_str(json_str)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid epistemic metric schema: {}", e)))?;
    Ok(true)
}
