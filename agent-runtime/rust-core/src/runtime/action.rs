use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Action {
    pub op: String,
    pub score: f32,
    pub expected_value: f32,
}
