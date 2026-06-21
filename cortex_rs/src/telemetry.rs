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
#[serde(tag = "kind")]
pub enum EpistemicMetric {
    Raw(RawMetric),
    Derived(DerivedMetric),
    Narrative(NarrativeClaim),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawMetric {
    pub name: String,
    pub value: f64,
    pub unit: String,
    pub source: String,          // e.g., "prometheus", "kernel_perf_counter"
    pub timestamp_epoch_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DerivedMetric {
    pub name: String,
    pub value: f64,
    pub unit: String,
    pub derivation: String,      // formula or reference to computation
    pub source_metrics: Vec<String>,  // names of input RawMetrics
    pub timestamp_epoch_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NarrativeClaim {
    pub claim: String,
    pub context: Option<String>,
    pub confidence: Option<String>,  // e.g., "low", "medium" — not a float
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
pub fn validate_metric_json(json_str: &str) -> PyResult<String> {
    let parsed: EpistemicMetric = serde_json::from_str(json_str)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!(
            "Telemetry validation failed: {e}"
        )))?;

    let kind = match parsed {
        EpistemicMetric::Raw(_) => "Raw",
        EpistemicMetric::Derived(_) => "Derived",
        EpistemicMetric::Narrative(_) => "Narrative",
    };

    Ok(kind.to_string())
}
