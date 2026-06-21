pub mod collision_bound;
pub mod edg;
pub mod event_schema;
pub mod hash_chain;
pub mod probabilistic_crdt;
pub mod replay;
pub mod scene_model;
pub mod smt_compiler;
pub mod vector_vault;

use edg::{EpistemicGraph, EpistemicNode, EpistemicStatus};
use pyo3::prelude::*;
use scene_model::{ContinuityRuleType, EdgeRule, SceneState};
use smt_compiler::{validate_scene_transition, GateStatus, Verdict};

/// CORTEX-Persist Cognitive Core Rust Extension (Enterprise EDG)
#[pymodule]
fn cortex_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<EpistemicStatus>()?;
    m.add_class::<EpistemicNode>()?;
    m.add_class::<EpistemicGraph>()?;
    m.add_class::<SceneState>()?;
    m.add_class::<EdgeRule>()?;
    m.add_class::<ContinuityRuleType>()?;
    m.add_class::<GateStatus>()?;
    m.add_class::<Verdict>()?;
    m.add_function(wrap_pyfunction!(validate_scene_transition, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::edg::{EpistemicGraph, EpistemicStatus};
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

        // Replay onto EpistemicGraph
        let graph = EpistemicGraph::new();
        replay_state(&graph, &chain.events).unwrap();

        // Check node 1
        assert_eq!(
            graph.get_node_status("mem_node_1").unwrap(),
            EpistemicStatus::Accepted
        );
        // Check node 2
        assert_eq!(
            graph.get_node_status("mem_node_2").unwrap(),
            EpistemicStatus::Accepted
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
            EpistemicStatus::Challenged
        );
    }
}
