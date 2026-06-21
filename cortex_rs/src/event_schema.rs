use serde::{Deserialize, Serialize};
use serde_json::Value;

/*
    CORE IDENTIFIERS
*/

pub type EventId = String;
pub type Hash = String;

/*
    EVENT TYPES
*/

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EventType {
    MemoryCreated,
    BeliefUpdated,
    DecisionMade,
    ContradictionDetected,
    ContradictionResolved,
    AuditCompleted,
    SnapshotCommitted,
}

/*
    TRUST LAYERS
*/

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EvidenceLevel {
    None,
    Basic,
    Traceable,
    Verified,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum IntegrityStatus {
    Unknown,
    Partial,
    Verified,
    Failed,
    Stale,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TaintStatus {
    None,
    Low,
    Medium,
    High,
    Unknown,
}

/*
    PROVENANCE
*/

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Provenance {
    pub source: String,
    pub agent_id: String,
    pub subsystem: String,
    pub parent_events: Vec<EventId>,
}

/*
    EPISTEMIC DELTA
*/

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceDelta {
    pub before: f32,
    pub after: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EntropyDelta {
    pub before: f32,
    pub after: f32,
}

/*
    IMPACT GRAPH
*/

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImpactRadius {
    pub affected_nodes: Vec<EventId>,
    pub invalidated_nodes: Vec<EventId>,
    pub propagation_depth: u32,
}

/*
    HUMAN MEMORY LAYER
*/

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HaikuDigest {
    pub title: String,
    pub line_one: String,
    pub line_two: String,
    pub line_three: String,
    pub generated_by: String,
}

/*
    MAIN EVENT ENVELOPE
*/

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LedgerEvent {
    /*
        Schema
    */
    pub schema_version: String,

    /*
        Identity
    */
    pub id: EventId,
    pub timestamp: u64,

    /*
        Event
    */
    pub event_type: EventType,

    /*
        Cryptographic chain
    */
    pub hash: Hash,
    pub previous_hash: Option<Hash>,

    /*
        Trust state
    */
    pub evidence_level: EvidenceLevel,
    pub integrity: IntegrityStatus,
    pub taint: TaintStatus,

    /*
        Reasoning state
    */
    pub confidence: Option<ConfidenceDelta>,
    pub entropy: Option<EntropyDelta>,

    /*
        Causal graph
    */
    pub provenance: Provenance,

    /*
        System effects
    */
    pub impact: Option<ImpactRadius>,

    /*
        Human layer
    */
    pub haiku: Option<HaikuDigest>,

    /*
        Extension field
    */
    pub metadata: Value,
}
