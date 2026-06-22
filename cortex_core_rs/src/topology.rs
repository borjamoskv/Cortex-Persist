// Immutable Epistemic Graph and Cognitive State Transitions (FSM)
// Replaces F# Cortex.Kernel.MemoryTopology, Cortex.Kernel.StateMachine, Cortex.Kernel.EpistemicNodes

use pyo3::prelude::*;
use std::collections::BTreeMap;
use crate::fixed60::Fixed60;
use crate::causal::{pop_count, causal_distance};

pub type Hash256 = (u64, u64, u64, u64);

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EpistemicPhase {
    Observation,
    Reflection,
    Decision,
    Execution,
    Verification,
}

impl EpistemicPhase {
    pub fn to_tag(&self) -> u32 {
        match self {
            EpistemicPhase::Observation => 0,
            EpistemicPhase::Reflection => 1,
            EpistemicPhase::Decision => 2,
            EpistemicPhase::Execution => 3,
            EpistemicPhase::Verification => 4,
        }
    }
}

pub enum TransitionResult {
    Advanced(EpistemicPhase, u32),
    Blocked(String),
    Halted,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Origin {
    HumanOperator(String),
    AutonomousSwarm(u32),
    SystemDaemon,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EpistemicNode {
    VerifiedHash { root: u32, distance: u16 },
    StochasticConjecture { origin: Origin, confidence: u16 },
    VoidAnergy,
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct MachineState {
    pub phase: EpistemicPhase,
    pub cycle: u32,
    pub exergy_accum: u32,
    pub trace_hash: u32,
}

impl MachineState {
    pub fn hash_transition(&self, next_phase: EpistemicPhase) -> u32 {
        let fnv_prime: u32 = 16777619;
        let combined = self.trace_hash ^ next_phase.to_tag() ^ self.cycle;
        combined.wrapping_mul(fnv_prime)
    }

    pub fn transition(&self, exergy_input: u32) -> TransitionResult {
        match self.phase {
            EpistemicPhase::Observation => {
                if exergy_input > 0 {
                    TransitionResult::Advanced(EpistemicPhase::Reflection, self.hash_transition(EpistemicPhase::Reflection))
                } else {
                    TransitionResult::Blocked("Zero exergy".to_string())
                }
            }
            EpistemicPhase::Reflection => {
                if exergy_input >= 10 {
                    TransitionResult::Advanced(EpistemicPhase::Decision, self.hash_transition(EpistemicPhase::Decision))
                } else {
                    TransitionResult::Blocked("Zero exergy".to_string())
                }
            }
            EpistemicPhase::Decision => {
                if exergy_input >= 50 {
                    TransitionResult::Advanced(EpistemicPhase::Execution, self.hash_transition(EpistemicPhase::Execution))
                } else {
                    TransitionResult::Blocked("Zero exergy".to_string())
                }
            }
            EpistemicPhase::Execution => {
                TransitionResult::Advanced(EpistemicPhase::Verification, self.hash_transition(EpistemicPhase::Verification))
            }
            EpistemicPhase::Verification => {
                TransitionResult::Advanced(EpistemicPhase::Observation, self.hash_transition(EpistemicPhase::Observation))
            }
        }
    }

    pub fn step_machine(&self, exergy_input: u32) -> MachineState {
        match self.transition(exergy_input) {
            TransitionResult::Advanced(next_phase, new_hash) => {
                let cycle_increment = match self.phase {
                    EpistemicPhase::Verification => 1,
                    _ => 0,
                };
                MachineState {
                    phase: next_phase,
                    cycle: self.cycle + cycle_increment,
                    exergy_accum: self.exergy_accum + exergy_input,
                    trace_hash: new_hash,
                }
            }
            TransitionResult::Blocked(_) => MachineState {
                phase: self.phase.clone(),
                cycle: self.cycle,
                exergy_accum: self.exergy_accum + exergy_input,
                trace_hash: self.trace_hash,
            },
            TransitionResult::Halted => self.clone(),
        }
    }
}

#[pyclass]
#[derive(Clone)]
pub struct CognitiveState {
    #[pyo3(get)]
    pub tick: u64,
    pub machine: MachineState,
    #[pyo3(get)]
    pub entropy_threshold: u16,
    pub graph: BTreeMap<Hash256, EpistemicNode>,
    #[pyo3(get)]
    pub global_confidence: Fixed60,
}

#[pymethods]
impl CognitiveState {
    #[new]
    pub fn new(initial_threshold: u16) -> Self {
        CognitiveState {
            tick: 0,
            machine: MachineState {
                phase: EpistemicPhase::Observation,
                cycle: 0,
                exergy_accum: 0,
                trace_hash: 0,
            },
            entropy_threshold: initial_threshold,
            graph: BTreeMap::new(),
            global_confidence: Fixed60::create(0),
        }
    }

    /// Pure Transition Engine: F(State, Stimulus, Exergy) -> State'
    /// We receive the stimulus as an option of raw values since PyO3 enum support is limited.
    /// In this wrapper we represent it simply with exergy_input and apply FSM logic,
    /// avoiding complex node ingestion for simplicity in the Python boundary unless needed.
    pub fn apply_tick(&self, exergy_input: u32) -> Self {
        // 1. Advance the pure State Machine
        let next_machine = self.machine.step_machine(exergy_input);

        // 2. Mathematical Maxwell Demon (Pure Thermodynamic Filtering)
        // Here we simulate the graph transition. If there was a stimulus, we'd check redundancy.
        // For the PyO3 wrapper, we will just step the machine and tick.
        
        let confidence_delta = Fixed60 { raw_value: 0 };

        // 3. Construct the new immutable universe state
        CognitiveState {
            tick: self.tick + 1,
            machine: next_machine,
            entropy_threshold: self.entropy_threshold,
            graph: self.graph.clone(),
            global_confidence: Fixed60::add(&self.global_confidence, &confidence_delta),
        }
    }

    pub fn get_machine_cycle(&self) -> u32 {
        self.machine.cycle
    }
}
