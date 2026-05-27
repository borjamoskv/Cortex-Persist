use std::collections::HashMap;

#[derive(Clone, Debug)]
pub struct State {
    pub last_hash: String,
    pub memory: HashMap<String, Vec<u8>>,
}
