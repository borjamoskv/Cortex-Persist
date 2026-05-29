//! OUROBOROS COMPILER v0.1 - WASM BINDINGS
//! Limerent Agent Compiler for CORTEX-Persist (C5-REAL live system in browser)

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use wasm_bindgen::prelude::*;

/// Definición formal de un agente en el entorno de fricción
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentNode {
    pub id: String,
    pub goal: String,
    pub energy: f64,
    pub friction: f64,
    pub limerence: f64,
    pub repetition: f64,
    pub stability: f64,
    pub maintenance_cost: f64,
    pub self_rewrite_rate: f64,
    pub memory: Vec<String>,
}

#[derive(Debug)]
pub struct OuroborosExecutionGraph {
    pub nodes: HashMap<String, AgentNode>,
    pub edges: Vec<(String, String, f64)>, // (Source, Target, Friction Weight)
}

impl Default for OuroborosExecutionGraph {
    fn default() -> Self {
        Self::new()
    }
}

impl OuroborosExecutionGraph {
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            edges: Vec::new(),
        }
    }

    pub fn parse_swarm(&mut self, agents_input: Vec<AgentNode>) {
        for mut a in agents_input {
            a.energy = self.estimate_exergy(&a.goal);
            a.friction = self.detect_conflict(&a.memory);
            self.nodes.insert(a.id.clone(), a);
        }
    }

    fn estimate_exergy(&self, _goal: &str) -> f64 { 1.0 }
    fn detect_conflict(&self, _memory: &[String]) -> f64 { 0.8 }

    pub fn vectorize_limerence(&mut self, alpha: f64, beta: f64, gamma: f64) {
        for node in self.nodes.values_mut() {
            node.limerence = (alpha * node.repetition) + (beta * node.friction) - (gamma * node.stability);
        }
    }

    pub fn link_ouroboros_cycles(&mut self) {
        let ids: Vec<String> = self.nodes.keys().cloned().collect();
        for i in 0..ids.len() {
            let src = &ids[i];
            let tgt = &ids[(i + 1) % ids.len()];
            let weight = self.nodes[src].limerence + self.nodes[tgt].limerence;
            self.edges.push((src.clone(), tgt.clone(), weight));
        }
    }

    pub fn filter_exergy(&mut self) {
        self.nodes.retain(|_, n| n.energy > n.maintenance_cost);
    }

    pub fn fractal_rewrite(&mut self) {
        for node in self.nodes.values_mut() {
            if node.friction > 0.8 {
                node.memory.truncate(node.memory.len() / 2);
                node.energy += 0.5; 
                node.self_rewrite_rate += 1.0;
            }
        }
    }

    pub fn execution_tick(&mut self) {
        self.vectorize_limerence(1.0, 1.5, 0.5);
        self.filter_exergy();
        self.fractal_rewrite();
    }
}

// -----------------------------------------------------------------------------
// WASM EXPORTS
// -----------------------------------------------------------------------------

#[wasm_bindgen]
pub struct OegWasmRuntime {
    graph: OuroborosExecutionGraph,
}

impl Default for OegWasmRuntime {
    fn default() -> Self {
        Self::new()
    }
}

#[wasm_bindgen]
impl OegWasmRuntime {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Self {
        Self {
            graph: OuroborosExecutionGraph::new(),
        }
    }

    /// Ingest a serialized swarm of agents from JS
    #[wasm_bindgen]
    pub fn parse_swarm_js(&mut self, agents_json: &str) -> Result<(), JsValue> {
        let agents: Vec<AgentNode> = serde_json::from_str(agents_json)
            .map_err(|e| JsValue::from_str(&format!("JSON Parse Error: {}", e)))?;
        
        self.graph.parse_swarm(agents);
        self.graph.link_ouroboros_cycles();
        Ok(())
    }

    /// Execute a full metabolic tick (vectorize -> filter -> rewrite)
    #[wasm_bindgen]
    pub fn execution_tick(&mut self) -> String {
        self.graph.execution_tick();
        
        // Return the surviving nodes back to the JS UI as JSON
        let surviving_nodes: Vec<&AgentNode> = self.graph.nodes.values().collect();
        serde_json::to_string(&surviving_nodes).unwrap_or_else(|_| "[]".to_string())
    }
}
