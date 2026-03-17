mod models;
mod storage;

use std::error::Error;
use models::BeliefObject;
use storage::EpisodicLog;
use uuid::Uuid;
use tempfile::tempdir;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    println!("Cortex-Persist: Cognitive Hypervisor (Phase 1)");
    
    // Demonstrate basic functionality
    let dir = tempdir()?;
    let log = EpisodicLog::new(dir.path())?;
    
    println!("Initialize EpisodicLog at {:?}", dir.path());
    
    let mut belief = BeliefObject::default();
    belief.proposition = "La pared de la consistencia es el foso tecnológico definitivo.".to_string();
    belief.confidence_score = 1.0;
    
    println!("Ingesting episode...");
    log.ingest_episode(&belief).await?;
    
    println!("Episode ingested: {}", belief.id);
    
    if let Some(retrieved) = log.get_episode(belief.id).await? {
        println!("Episode retrieved successfully: '{}'", retrieved.proposition);
    }
    
    Ok(())
}
