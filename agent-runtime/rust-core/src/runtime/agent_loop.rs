use crate::runtime::state::State;
use crate::runtime::safety::SafetyFilter;
use crate::runtime::scheduler::Scheduler;
use crate::ffi::python_bridge::PythonBridge;
use crate::memory::event_store::EventStore;
use tracing::{info, warn};

pub async fn run_agent_loop(mut state: State, mut policy: PythonBridge, max_steps: i64) -> anyhow::Result<()> {
    loop {
        if state.step >= max_steps {
            info!("Max steps reached. Halting execution.");
            break;
        }

        let obs = state.observe();

        // Query Sanedrín (MCTS + ValueNet) in Python
        let action_dist = policy.get_actions(obs).await?;

        // Scheduler truncates
        let scheduled = Scheduler::schedule(action_dist);

        // Safety Filter enforces C5-REAL bounds
        if let Some(action) = SafetyFilter::apply(scheduled, &state) {
            info!("Executing action: {} (Expected Value: {})", action.op, action.expected_value);
            
            // Execute Action (Mock executor)
            let result = format!("Executed {}", action.op);

            // Mutate State
            state.update(&action, result);

            // Persist Trace
            EventStore::append(state.snapshot())?;
        } else {
            warn!("Safety Filter rejected all candidate actions. Halting loop.");
            break;
        }
    }
    Ok(())
}
