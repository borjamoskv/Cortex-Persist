use serde::{Deserialize, Serialize};
use uuid::Uuid;
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum BeliefStatus {
    Active,
    Contested,
    Subsumed,
    Discarded,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BeliefObject {
    pub id: Uuid, // UUIDv7
    pub proposition: String,
    pub semantic_embedding: Option<Vec<f32>>,
    pub confidence_score: f64,
    pub variance: f64,
    pub status: BeliefStatus,
    pub decay_rate: f64,
    pub was_generated_by: String,
    pub was_attributed_to: String,
    pub entails: Vec<Uuid>,
    pub discards: Vec<Uuid>,
    pub created_at: DateTime<Utc>,
}

impl Default for BeliefObject {
    fn default() -> Self {
        Self {
            id: Uuid::now_v7(),
            proposition: String::new(),
            semantic_embedding: None,
            confidence_score: 1.0,
            variance: 0.0,
            status: BeliefStatus::Active,
            decay_rate: 0.0,
            was_generated_by: "system".to_string(),
            was_attributed_to: "system".to_string(),
            entails: vec![],
            discards: vec![],
            created_at: Utc::now(),
        }
    }
}
