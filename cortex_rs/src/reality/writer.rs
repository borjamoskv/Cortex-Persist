use crossbeam_channel::{unbounded, Sender, bounded};
use std::fs::OpenOptions;
use std::io::{BufWriter, Write};
use std::thread;
use crate::reality::swarm_sync::SwarmSync;

pub struct RealityWriter {
    sender: Sender<(String, Sender<()>)>,
    _swarm_sync: SwarmSync, // Keeps the Zenoh runtime alive
}

impl RealityWriter {
    pub fn new(ledger_path: &str) -> Self {
        let (sender, receiver) = unbounded::<(String, Sender<()>)>();
        let (zenoh_tx, zenoh_rx) = unbounded::<String>();
        
        let swarm_sync = SwarmSync::new(zenoh_rx);
        let path = ledger_path.to_string();

        thread::spawn(move || {
            let file = OpenOptions::new()
                .create(true)
                .append(true)
                .open(&path)
                .expect("Failed to open ledger file for append");
            let mut writer = BufWriter::new(file);

            for (msg, ack_tx) in receiver {
                if let Err(e) = writeln!(writer, "{}", msg) {
                    eprintln!("Failed to write to epistemic ledger: {}", e);
                }
                if let Err(e) = writer.flush() {
                    eprintln!("Failed to flush epistemic ledger: {}", e);
                }
                // Broadcast to the Swarm via Zenoh
                let _ = zenoh_tx.send(msg);
                
                // Send durability ACK back to the ingest thread
                let _ = ack_tx.send(());
            }
        });

        Self { 
            sender,
            _swarm_sync: swarm_sync 
        }
    }

    pub fn write_claim(&self, claim_json: &str) -> Result<(), String> {
        let (ack_tx, ack_rx) = bounded(1);
        if let Err(e) = self.sender.send((claim_json.to_string(), ack_tx)) {
            return Err(format!("Failed to send claim to async writer: {}", e));
        }
        ack_rx.recv().map_err(|_| "Failed to receive durability ACK from WAL flush. Potential data loss.".to_string())?;
        Ok(())
    }
}
