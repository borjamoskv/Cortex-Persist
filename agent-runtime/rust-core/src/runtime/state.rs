use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct State {
    pub obs_vector: Vec<f32>,
    pub blacklist: Vec<String>,
    pub step: i64,
}

impl State {
    pub fn new() -> Self {
        Self {
            obs_vector: vec![0.0; 128], // Dim: 128 matching Python
            blacklist: vec!["rm -rf /".to_string(), "DROP TABLE".to_string()],
            step: 0,
        }
    }

    pub fn observe(&self) -> &State {
        self
    }

    pub fn update(&mut self, _action: &super::action::Action, _result: String) {
        self.step += 1;
        // In a real C5-REAL execution, we would update obs_vector based on result.
    }

    pub fn snapshot(&self) -> StateSnapshot {
        StateSnapshot {
            step: self.step,
            obs: self.obs_vector.clone(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateSnapshot {
    pub step: i64,
    pub obs: Vec<f32>,
}
