use rocksdb::{DB, Options};
use std::path::Path;
use anyhow::{Result, Context};
use std::sync::Arc;
use tokio::task;
use uuid::Uuid;

use crate::models::BeliefObject;

#[derive(Clone)]
pub struct EpisodicLog {
    db: Arc<DB>,
}

impl EpisodicLog {
    pub fn new<P: AsRef<Path>>(path: P) -> Result<Self> {
        let mut opts = Options::default();
        opts.create_if_missing(true);
        let db = DB::open(&opts, path).context("Failed to open RocksDB for Episodic Log")?;
        Ok(Self { db: Arc::new(db) })
    }

    pub async fn ingest_episode(&self, belief: &BeliefObject) -> Result<()> {
        let db = self.db.clone();
        let belief_clone = belief.clone();
        
        // E/S asíncrona usando spawn_blocking para no bloquear el executor de Tokio con RocksDB
        task::spawn_blocking(move || -> Result<()> {
            let key = belief_clone.id.into_bytes();
            let val = serde_json::to_vec(&belief_clone)?;
            db.put(key, val)?;
            Ok(())
        })
        .await
        .context("Task execution failed")??;
        
        Ok(())
    }

    pub async fn get_episode(&self, id: Uuid) -> Result<Option<BeliefObject>> {
        let db = self.db.clone();
        task::spawn_blocking(move || -> Result<Option<BeliefObject>> {
            let key = id.into_bytes();
            match db.get(key)? {
                Some(val) => {
                    let belief: BeliefObject = serde_json::from_slice(&val)?;
                    Ok(Some(belief))
                }
                None => Ok(None),
            }
        })
        .await
        .context("Task execution failed")?
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_ingest_and_get() -> Result<()> {
        let dir = tempdir()?;
        let log = EpisodicLog::new(dir.path())?;
        
        let mut belief = BeliefObject::default();
        belief.proposition = "El cielo es azul".to_string();
        
        log.ingest_episode(&belief).await?;
        
        let retrieved = log.get_episode(belief.id).await?;
        assert!(retrieved.is_some());
        
        let retrieved = retrieved.unwrap();
        assert_eq!(retrieved.proposition, "El cielo es azul");
        assert_eq!(retrieved.id, belief.id);
        
        Ok(())
    }
}
