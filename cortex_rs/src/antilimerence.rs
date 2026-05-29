use std::time::{SystemTime, UNIX_EPOCH};
use serde::{Serialize, Deserialize};
use pyo3::prelude::*;
use pyo3::types::PyList;

/// ⚡ CORTEX-PERSIST: ANTI-LIMERENCE RUNTIME
/// Prevención de Overfitting Cognitivo y Adoración de Modelos (Model Worship).

const LIMERENCE_THRESHOLD: f64 = 0.85;
const INCUBATION_GRACE_PERIOD_SEC: u64 = 86400; // Edge case resuelto: fase creativa

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BeliefNode {
    pub id: String,
    pub internal_coherence: f64,  // Estética teórica / Overfitting (0.0 a 1.0+)
    pub empirical_yield: f64,     // Verdad externa / Exergía predictiva
    pub birth_timestamp: u64,
    pub last_falsification: u64,
}

impl BeliefNode {
    pub fn exergy_score(&self) -> f64 {
        // La coherencia interna se cobra como un pasivo (penalty cuadrático)
        let coherence_penalty = self.internal_coherence.powf(2.0) * 0.15;
        self.empirical_yield - coherence_penalty
    }
    
    pub fn is_limerent(&self) -> bool {
        let age = current_timestamp() - self.birth_timestamp;
        
        // Evitamos matar ideas en fase de incubación (arte/compresión pura)
        if age < INCUBATION_GRACE_PERIOD_SEC { return false; }

        // Limerencia = La teoría cuesta más mantenerla que la exergía que produce
        self.exergy_score() < 0.0 && self.internal_coherence > LIMERENCE_THRESHOLD
    }
}

pub trait FalsificationRuntime {
    fn inject_reality_friction(&mut self, belief_id: &str, reality_delta: f64);
    fn execute_belief_kill_switch(&mut self) -> Vec<String>;
}

#[pyclass]
pub struct AntiLimerenceTopology {
    pub active_beliefs: Vec<BeliefNode>,
}

#[pymethods]
impl AntiLimerenceTopology {
    #[new]
    pub fn new() -> PyResult<Self> {
        Ok(AntiLimerenceTopology {
            active_beliefs: Vec::new(),
        })
    }

    /// Añade una nueva creencia/teoría a la topología
    pub fn incubate_belief(&mut self, belief_id: String) -> PyResult<()> {
        self.active_beliefs.push(BeliefNode {
            id: belief_id,
            internal_coherence: 0.1, // Empieza baja
            empirical_yield: 0.0,
            birth_timestamp: current_timestamp(),
            last_falsification: current_timestamp(),
        });
        Ok(())
    }

    /// Expone el API a Python para inyectar fricción del mundo real
    pub fn inject_friction(&mut self, belief_id: &str, reality_delta: f64) -> PyResult<()> {
        if let Some(node) = self.active_beliefs.iter_mut().find(|b| b.id == belief_id) {
            node.empirical_yield += reality_delta;
            node.last_falsification = current_timestamp();
            
            // Si la realidad ataca la teoría (reality_delta < 0), aumenta coherencia interna
            // simulando el overfitting defensivo.
            if reality_delta < 0.0 {
                node.internal_coherence += 0.08; 
            }
        }
        Ok(())
    }

    /// Dispara el mecanismo Ouroboros devolviendo las creencias que han muerto por limerencia
    pub fn execute_kill_switch<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        let mut purged = Vec::new();
        self.active_beliefs.retain(|node| {
            if node.is_limerent() {
                purged.push(node.id.clone());
                false
            } else {
                true
            }
        });
        
        // Retornar lista de IDs a Python
        let py_list = PyList::empty(py);
        for id in purged {
            py_list.append(id)?;
        }
        Ok(py_list)
    }

    /// Consulta rápida de salud termodinámica
    pub fn get_belief_status(&self, belief_id: &str) -> PyResult<Option<(f64, f64, f64)>> {
        if let Some(node) = self.active_beliefs.iter().find(|b| b.id == belief_id) {
            Ok(Some((node.internal_coherence, node.empirical_yield, node.exergy_score())))
        } else {
            Ok(None)
        }
    }
}

fn current_timestamp() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()
}
