mod event;
mod state;
mod crypto;
mod verify;
mod kernel;
mod proof;
mod error;
mod memory_dag;

use crate::{event::Event, state::State};

fn main() {
    let state = State {
        last_hash: "GENESIS".to_string(),
        memory: std::collections::HashMap::new(),
    };
    
    let event = Event {
        id: "e1".to_string(),
        prev_hash: "GENESIS".to_string(),
        payload: b"hello".to_vec(),
        agent_id: "agent_01".to_string(),
        signature: vec![],
    };
    
    match kernel::apply_event(state, event) {
        Ok(new_state) => {
            println!("State updated: {:?}", new_state);
        }
        Err(e) => {
            println!("Kernel rejected event: {}", e);
        }
    }
}
