use crate::edg::{RetrievalGraph, RetrievalNode, ValidationStatus};
use crate::event_schema::{EventType, LedgerEvent};
use crate::hash_chain::verify_event;

/// Replays a sequence of LedgerEvents onto the RetrievalGraph.
/// First validates the cryptographic integrity of the chain.
pub fn replay_state(graph: &RetrievalGraph, events: &[LedgerEvent]) -> Result<(), String> {
    // 1. Verify cryptographic integrity of the incoming sequence
    for i in 0..events.len() {
        let prev = if i > 0 { Some(&events[i - 1]) } else { None };
        match verify_event(&events[i], prev) {
            Ok(true) => {}
            Ok(false) => {
                return Err(format!(
                    "Cryptographic verification failed for event at index {}",
                    i
                ))
            }
            Err(e) => return Err(format!("Error verifying event at index {}: {:?}", i, e)),
        }
    }

    // 2. Replay events onto the RetrievalGraph
    for event in events {
        match event.event_type {
            EventType::MemoryCreated => {
                let node_id = event
                    .metadata
                    .get("node_id")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| {
                        "MemoryCreated event missing 'node_id' in metadata".to_string()
                    })?;

                let confidence = event
                    .metadata
                    .get("confidence")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(1.0);

                let node = RetrievalNode::new(node_id.to_string(), confidence);
                graph.add_node(node);

                // Process dependency mappings if present
                if let Some(supports) = event.metadata.get("supports").and_then(|v| v.as_array()) {
                    for sup in supports {
                        if let Some(sup_id) = sup.as_str() {
                            let _ = graph.add_dependency(node_id, sup_id);
                        }
                    }
                }
                if let Some(supported_by) = event
                    .metadata
                    .get("supported_by")
                    .and_then(|v| v.as_array())
                {
                    for sup in supported_by {
                        if let Some(sup_id) = sup.as_str() {
                            let _ = graph.add_dependency(sup_id, node_id);
                        }
                    }
                }
            }
            EventType::BeliefUpdated => {
                let node_id = event
                    .metadata
                    .get("node_id")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| {
                        "BeliefUpdated event missing 'node_id' in metadata".to_string()
                    })?;

                if let Some(confidence) = event.metadata.get("confidence").and_then(|v| v.as_f64())
                {
                    if let Some(mut node) = graph.nodes.get_mut(node_id) {
                        node.confidence = confidence;
                    }
                }

                if let Some(status_str) = event.metadata.get("status").and_then(|v| v.as_str()) {
                    let status = ValidationStatus::from_legacy(status_str);
                    if let Some(mut node) = graph.nodes.get_mut(node_id) {
                        node.status = status;
                    }
                }
            }
            EventType::ContradictionDetected => {
                if let Some(ref impact) = event.impact {
                    for node_id in &impact.invalidated_nodes {
                        graph.invalidate_node(node_id);
                    }
                } else if let Some(invalidated_array) = event
                    .metadata
                    .get("invalidated_nodes")
                    .and_then(|v| v.as_array())
                {
                    for val in invalidated_array {
                        if let Some(node_id) = val.as_str() {
                            graph.invalidate_node(node_id);
                        }
                    }
                }
            }
            _ => {
                // Non-mutating events for the in-memory RetrievalGraph (e.g. AuditCompleted, SnapshotCommitted)
            }
        }
    }

    Ok(())
}
