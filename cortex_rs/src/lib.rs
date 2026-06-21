pub mod ast_hash;
pub mod collision_bound;
pub mod edg;
pub mod event_schema;
pub mod hash_chain;
pub mod probabilistic_crdt;
pub mod replay;
pub mod scene_model;
pub mod smt_compiler;
pub mod telemetry;
pub mod vector_vault;
pub mod reality;
pub mod bft;
pub mod causal;
pub mod retrieval;
pub mod babylon;
pub mod mee;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum CortexEvent {
    ClaimSubmitted,
    ClaimVerified,
    ClaimRejected,
    StateMutated,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum OriginType {
    FrontierRevEng,
    SotaVectorEngine,
    HumanMosaic,
    LLMInference,
    SystemDaemon,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SystemLayer {
    C5Real,
    C4Sim,
    Playground,
}

use edg::{RetrievalGraph, RetrievalNode, ValidationStatus};
use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use scene_model::{ContinuityRuleType, EdgeRule, SceneState};
use smt_compiler::{validate_scene_transition, GateStatus, Verdict};
use telemetry::validate_metric_json;
use bft::exergy::{ExergyGuard, ExergyMutation};
use causal::solver::{CausalCompiler, ConsensusVerdict};
use retrieval::vaccine::{RetrievalFact, ValidationStatus as VacStatus, VaccineGuard};

/// Valida y registra un claim desde Python.
/// Retorna el status final como string.
#[pyfunction]
pub fn ingest_reality_claim(
    ledger_path: &str,
    claim_json: &str,
    now_epoch_ms: u64,
) -> PyResult<String> {
    let claim: reality::claim::RealityClaim = serde_json::from_str(claim_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid claim JSON: {e}")))?;

    let registry = reality::registry::RealityRegistry::new(ledger_path);

    let status = registry
        .ingest(claim, now_epoch_ms)
        .map_err(|e| PyValueError::new_err(format!("Ingestion failed: {e}")))?;

    let status_str = match status {
        reality::claim::ClaimStatus::Verified => "verified",
        reality::claim::ClaimStatus::Rejected => "rejected",
        reality::claim::ClaimStatus::Pending  => "pending",
        reality::claim::ClaimStatus::Unknown  => "unknown",
    };

    Ok(status_str.to_string())
}

#[pyfunction]
pub fn validate_exergy_mutation(mutation_json: &str, valid_nodes: Vec<String>) -> PyResult<()> {
    let mutation: ExergyMutation = serde_json::from_str(mutation_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid mutation JSON: {}", e)))?;
    
    if mutation.rul_claim_id.is_none() {
        return Err(PyValueError::new_err("MissingRULClaim"));
    }

    let guard = ExergyGuard {
        cluster_size: 9,
        max_delta_per_epoch: 100.0,
    };
    
    guard.validate(&mutation, &valid_nodes)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

#[pyfunction]
pub fn verify_causal_assertion(assertion: &str) -> PyResult<String> {
    let compiler = CausalCompiler::new();
    let verdict = compiler.verify(assertion);
    let s = match verdict {
        ConsensusVerdict::Valid => "valid",
        ConsensusVerdict::Invalid => "invalid",
        ConsensusVerdict::Undetermined => "undetermined",
    };
    Ok(s.to_string())
}

#[pyfunction]
pub fn create_staging_fact(agent_id: &str, hypothesis: &str) -> PyResult<String> {
    let fact = RetrievalFact {
        fact_id: "fact_test".into(),
        agent_id: agent_id.to_string(),
        hypothesis: hypothesis.to_string(),
        validation_status: VacStatus::Staging,
        zk_proof: Some("test_proof".into()),
        created_at_epoch_ms: 1717027200000,
        sealed_at_epoch_ms: None,
        wal_event_hash: None,
    };
    serde_json::to_string(&fact)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

#[pyfunction]
pub fn can_read_fact(fact_json: &str, agent_id: &str) -> PyResult<bool> {
    let fact: RetrievalFact = serde_json::from_str(fact_json)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(VaccineGuard::can_read(&fact, agent_id))
}

#[pyfunction]
pub fn try_seal_fact(fact_json: &str, wal_event_hash: &str, valid: bool) -> PyResult<String> {
    let mut fact: RetrievalFact = serde_json::from_str(fact_json)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    
    let validator = |_proof: &str| valid;
    VaccineGuard::try_seal(&mut fact, wal_event_hash, &validator)
        .map_err(|e| PyValueError::new_err(e))?;
    
    serde_json::to_string(&fact)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

#[pyfunction]
pub fn calculate_entropy_b60(data: &[u8]) -> PyResult<babylon::Babylon60> {
    let mut counts = [0usize; 256];
    for &b in data {
        counts[b as usize] += 1;
    }
    let len = data.len() as f64;
    let mut entropy = 0.0;
    if len > 0.0 {
        for &count in &counts {
            if count > 0 {
                let p = count as f64 / len;
                entropy -= p * p.log2();
            }
        }
    }
    Ok(babylon::Babylon60::from_float(entropy))
}


/// CORTEX-Persist Cognitive Core Rust Extension (Enterprise KRGS)
#[pymodule]
fn cortex_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ValidationStatus>()?;
    m.add_class::<RetrievalNode>()?;
    m.add_class::<RetrievalGraph>()?;
    m.add_class::<SceneState>()?;
    m.add_class::<EdgeRule>()?;
    m.add_class::<ContinuityRuleType>()?;
    m.add_class::<GateStatus>()?;
    m.add_class::<Verdict>()?;
    m.add_class::<babylon::Babylon60>()?;
    m.add_function(wrap_pyfunction!(validate_scene_transition, m)?)?;
    m.add_function(wrap_pyfunction!(validate_metric_json, m)?)?;
    m.add_function(wrap_pyfunction!(ingest_reality_claim, m)?)?;
    m.add_function(wrap_pyfunction!(validate_exergy_mutation, m)?)?;
    m.add_function(wrap_pyfunction!(verify_causal_assertion, m)?)?;
    m.add_function(wrap_pyfunction!(create_staging_fact, m)?)?;
    m.add_function(wrap_pyfunction!(can_read_fact, m)?)?;
    m.add_function(wrap_pyfunction!(try_seal_fact, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_entropy_b60, m)?)?;
    m.add_function(wrap_pyfunction!(reality::reader::load_verified_reality, m)?)?;
    m.add_function(wrap_pyfunction!(mee::ffi::execute_mee_transfer, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::edg::{RetrievalGraph, ValidationStatus};
    use super::event_schema::{
        EventType, EvidenceLevel, IntegrityStatus, LedgerEvent, Provenance, TaintStatus,
    };
    use super::hash_chain::HashChain;
    use super::replay::replay_state;
    use serde_json::json;

    #[test]
    fn test_event_hashing_and_replay() {
        let mut chain = HashChain::new();

        let event1 = LedgerEvent {
            schema_version: "1.0.0".to_string(),
            id: "evt_001".to_string(),
            timestamp: 123456789,
            event_type: EventType::MemoryCreated,
            hash: String::new(), // to be computed
            previous_hash: None,
            evidence_level: EvidenceLevel::Basic,
            integrity: IntegrityStatus::Unknown,
            taint: TaintStatus::None,
            confidence: None,
            entropy: None,
            provenance: Provenance {
                source: "test".to_string(),
                agent_id: "agent_01".to_string(),
                subsystem: "core".to_string(),
                parent_events: vec![],
            },
            impact: None,
            haiku: None,
            metadata: json!({
                "node_id": "mem_node_1",
                "confidence": 0.85,
                "supports": ["mem_node_2"]
            }),
        };

        let event2 = LedgerEvent {
            schema_version: "1.0.0".to_string(),
            id: "evt_002".to_string(),
            timestamp: 123456790,
            event_type: EventType::MemoryCreated,
            hash: String::new(), // to be computed
            previous_hash: None,
            evidence_level: EvidenceLevel::Basic,
            integrity: IntegrityStatus::Unknown,
            taint: TaintStatus::None,
            confidence: None,
            entropy: None,
            provenance: Provenance {
                source: "test".to_string(),
                agent_id: "agent_01".to_string(),
                subsystem: "core".to_string(),
                parent_events: vec!["evt_001".to_string()],
            },
            impact: None,
            haiku: None,
            metadata: json!({
                "node_id": "mem_node_2",
                "confidence": 0.90
            }),
        };

        // Append to chain
        let hash1 = chain.append_event(event1).unwrap();
        let hash2 = chain.append_event(event2).unwrap();

        assert_eq!(chain.events.len(), 2);
        assert_eq!(chain.events[0].hash, hash1);
        assert_eq!(chain.events[1].previous_hash.as_ref().unwrap(), &hash1);
        assert_eq!(chain.events[1].hash, hash2);

        // Verify the entire chain
        assert!(chain.verify_chain().unwrap());

        // Replay onto RetrievalGraph
        let graph = RetrievalGraph::new();
        replay_state(&graph, &chain.events).unwrap();

        // Check node 1
        assert_eq!(
            graph.get_node_status("mem_node_1").unwrap(),
            ValidationStatus::Proven
        );
        // Check node 2
        assert_eq!(
            graph.get_node_status("mem_node_2").unwrap(),
            ValidationStatus::Proven
        );

        // Modify belief
        let event3 = LedgerEvent {
            schema_version: "1.0.0".to_string(),
            id: "evt_003".to_string(),
            timestamp: 123456791,
            event_type: EventType::BeliefUpdated,
            hash: String::new(),
            previous_hash: None,
            evidence_level: EvidenceLevel::Basic,
            integrity: IntegrityStatus::Unknown,
            taint: TaintStatus::None,
            confidence: None,
            entropy: None,
            provenance: Provenance {
                source: "test".to_string(),
                agent_id: "agent_01".to_string(),
                subsystem: "core".to_string(),
                parent_events: vec!["evt_002".to_string()],
            },
            impact: None,
            haiku: None,
            metadata: json!({
                "node_id": "mem_node_1",
                "status": "Challenged"
            }),
        };

        chain.append_event(event3).unwrap();
        replay_state(&graph, &chain.events).unwrap();

        assert_eq!(
            graph.get_node_status("mem_node_1").unwrap(),
            ValidationStatus::Challenged
        );
    }
}
