use std::fs::OpenOptions;
use std::io::Write;
use crate::runtime::state::StateSnapshot;

pub struct EventStore;

impl EventStore {
    pub fn append(snapshot: StateSnapshot) -> anyhow::Result<()> {
        let encoded = serde_json::to_string(&snapshot)?;
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open("ledger.aof")?;
        
        writeln!(file, "{}", encoded)?;
        Ok(())
    }
}
