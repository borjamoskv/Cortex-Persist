// [C5-REAL] Exergy-Maximized
use std::collections::HashMap;

#[derive(Clone, Debug, PartialEq)]
pub enum AgentStatus {
    Active,
    Quarantined,
    Tombstoned,
    Purged,
}

#[derive(Clone, Debug)]
pub struct State {
    pub last_hash: String,
    pub memory: HashMap<String, Vec<u8>>,
    pub reputation: HashMap<String, u32>,
    pub agent_lifecycle: HashMap<String, AgentStatus>,
    pub public_keys: HashMap<String, [u8; 32]>,
}
