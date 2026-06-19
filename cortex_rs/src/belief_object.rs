use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[pyclass(from_py_object)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum BeliefState {
    Active,
    Contested,
    Subsumed,
    Discarded,
    Archived,
    Orphaned,
}

#[pyclass(from_py_object)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RelationType {
    Entails,
    Discards,
    DependsOn,
    Supersedes,
}

#[pyclass(from_py_object)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProvenanceEnvelope {
    #[pyo3(get, set)]
    pub source_hash: String,
    #[pyo3(get, set)]
    pub source_type: String, // agent, tool, human
    #[pyo3(get, set)]
    pub tenant_id: String,
    #[pyo3(get, set)]
    pub signer_id: String,
    #[pyo3(get, set)]
    pub signature: String,
    #[pyo3(get, set)]
    pub created_at: i64,
}

#[pymethods]
impl ProvenanceEnvelope {
    #[new]
    pub fn new(
        source_hash: String,
        source_type: String,
        tenant_id: String,
        signer_id: String,
        signature: String,
        created_at: i64,
    ) -> Self {
        ProvenanceEnvelope {
            source_hash,
            source_type,
            tenant_id,
            signer_id,
            signature,
            created_at,
        }
    }
}

#[pyclass(from_py_object)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BeliefRelation {
    #[pyo3(get, set)]
    pub relation_type: RelationType,
    pub target_id: Uuid,
}

#[pymethods]
impl BeliefRelation {
    #[new]
    pub fn new(relation_type: RelationType, target_id_str: &str) -> PyResult<Self> {
        let target_id = Uuid::parse_str(target_id_str)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        Ok(BeliefRelation {
            relation_type,
            target_id,
        })
    }
    
    #[getter]
    pub fn target_id(&self) -> String {
        self.target_id.to_string()
    }
}

// Note: PyO3 does not easily support enums with payloads directly as #[pyclass] in older versions,
// but we will expose a simplified interface or wrappers for Python.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PropositionPayload {
    Boolean(bool),
    Categorical(String),
    Scalar(f64),
    Set(Vec<String>),
    Reference { uri: String, kind: String },
}

#[pyclass(from_py_object)]
#[derive(Debug, Clone)]
pub struct BeliefObject {
    pub id: Uuid,
    #[pyo3(get, set)]
    pub proposition_key: String,
    pub payload: PropositionPayload,
    #[pyo3(get, set)]
    pub confidence_score: f32,
    #[pyo3(get, set)]
    pub uncertainty: f32,
    #[pyo3(get, set)]
    pub decay_rate: f32,
    #[pyo3(get, set)]
    pub state: BeliefState,
    #[pyo3(get, set)]
    pub provenance: ProvenanceEnvelope,
    #[pyo3(get, set)]
    pub relations: Vec<BeliefRelation>,
    #[pyo3(get, set)]
    pub supporting_roots: Vec<String>,
    #[pyo3(get, set)]
    pub dependency_epoch: u64,
    #[pyo3(get, set)]
    pub timestamp_created: i64,
    #[pyo3(get, set)]
    pub timestamp_last_verified: i64,
    #[pyo3(get, set)]
    pub semantic_version: u32,
}

#[pymethods]
impl BeliefObject {
    #[new]
    #[pyo3(signature = (proposition_key, confidence_score, uncertainty, decay_rate, state, provenance, timestamp_created, timestamp_last_verified, semantic_version))]
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        proposition_key: String,
        confidence_score: f32,
        uncertainty: f32,
        decay_rate: f32,
        state: BeliefState,
        provenance: ProvenanceEnvelope,
        timestamp_created: i64,
        timestamp_last_verified: i64,
        semantic_version: u32,
    ) -> Self {
        BeliefObject {
            id: Uuid::new_v4(),
            proposition_key,
            payload: PropositionPayload::Boolean(true), // Default for now
            confidence_score,
            uncertainty,
            decay_rate,
            state,
            provenance,
            relations: Vec::new(),
            supporting_roots: Vec::new(),
            dependency_epoch: 0,
            timestamp_created,
            timestamp_last_verified,
            semantic_version,
        }
    }

    #[getter]
    pub fn id(&self) -> String {
        self.id.to_string()
    }
}
