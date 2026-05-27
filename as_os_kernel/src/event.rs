use serde::{Serialize, Deserialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Event {
    pub id: String,
    pub prev_hash: String,
    pub payload: Vec<u8>,
    pub agent_id: String,
    pub signature: Vec<u8>,
}
