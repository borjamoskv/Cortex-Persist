use crossbeam_channel::Receiver;
use zenoh::config::Config;

pub struct SwarmSync {
    // Thread handle for the background tokio runtime
    _thread: std::thread::JoinHandle<()>,
}

impl SwarmSync {
    /// Spawns a dedicated Tokio runtime thread to handle Zenoh pub/sub
    pub fn new(receiver: Receiver<String>) -> Self {
        let thread = std::thread::spawn(move || {
            // Create a dedicated single-threaded or multi-threaded tokio runtime for Zenoh
            let rt = tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
                .expect("Failed to build tokio runtime for SwarmSync");

            rt.block_on(async move {
                // Initialize Zenoh with default config
                let config = Config::default();
                let session = match zenoh::open(config).await {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("SwarmSync Zenoh failed to open session: {:?}", e);
                        return;
                    }
                };

                let publisher = match session.declare_publisher("cortex/ledger/claims").await {
                    Ok(p) => p,
                    Err(e) => {
                        eprintln!("SwarmSync Zenoh failed to declare publisher: {:?}", e);
                        return;
                    }
                };

                println!("[C5-REAL] SwarmSync Zenoh publisher active on 'cortex/ledger/claims'");

                // Continuously receive messages from the crossbeam channel and publish
                for msg in receiver {
                    if let Err(e) = publisher.put(msg).await {
                        eprintln!("SwarmSync Zenoh failed to publish claim: {:?}", e);
                    }
                }
            });
        });

        Self { _thread: thread }
    }
}
