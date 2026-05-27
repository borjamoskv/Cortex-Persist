use crate::event::Event;

pub struct MemoryDAG {
    pub chain: Vec<Event>,
}

impl MemoryDAG {
    pub fn new() -> Self {
        Self { chain: vec![] }
    }
    pub fn tip_hash(&self) -> String {
        self.chain
            .last()
            .map(|e| e.id.clone())
            .unwrap_or_else(|| "GENESIS".to_string())
    }
}
