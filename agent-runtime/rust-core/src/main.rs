pub mod runtime;
pub mod memory;
pub mod ffi;

use ffi::python_bridge::PythonBridge;
use runtime::state::State;
use tracing::info;
use tracing_subscriber;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();

    info!("CORTEX-Persist N4 Rust Kernel Booting...");

    // Wait for Python Policy Engine to be ready
    // In production, use exponential backoff
    let policy_endpoint = "http://127.0.0.1:50051".to_string();
    info!("Connecting to Python Policy Engine at {}", policy_endpoint);
    let policy_bridge = PythonBridge::new(policy_endpoint).await?;

    let initial_state = State::new();

    // Start execution loop (max 10 steps for demo)
    info!("Entering C5-REAL execution loop...");
    runtime::agent_loop::run_agent_loop(initial_state, policy_bridge, 10).await?;

    info!("Execution completed successfully.");
    Ok(())
}
