<!-- [C5-REAL] Exergy-Maximized -->
# AGENTS.ARCHI — SELF-MODIFYING TOPOLOGY ENGINE (SMTE)

> **STATUS:** C5-REAL++
> **PARADIGMA:** Biología Computacional con Ruido Termodinámico
> **REGLA AXIOMÁTICA:** El sistema no tiene agentes fijos. Los agentes son órganos transitorios.

## 1. CORE ABSTRACTION: AGENT GENOME

```rust
#[derive(Clone, Serialize, Deserialize)]
pub struct AgentGene {
    pub id: String,
    pub role: String,
    pub behavior_vector: Vec<f32>,
    pub constraints: Vec<String>,
    pub mutation_rate: f32,
    pub exergy_bias: f32,
    pub lifetime: u64,
}
```

## 2. LIVE TOPOLOGY STATE

```rust
pub struct Topology {
    pub agents: HashMap<String, AgentGene>,
    pub connections: Vec<(String, String)>,
}
```

## 3. MUTATION EVENTS (CORTEX-PERSIST EXTENSION)

```rust
pub enum TopologyEvent {
    SpawnGene { template: String },
    MutateGene { agent_id: String, delta: Vec<f32> },
    MergeGenes { a: String, b: String },
    SplitGene { agent_id: String },
    KillGene { agent_id: String },
    RewriteBehavior {
        agent_id: String,
        new_constraints: Vec<String>
    }
}
```

## 4. SELF-MODIFICATION LOOP & FITNESS

```rust
pub fn fitness(gene: &AgentGene) -> f32 {
    let output = gene.behavior_vector.iter().sum::<f32>();
    let complexity = gene.constraints.len() as f32;
    output / (complexity + 1.0)
}

pub fn prune_low_exergy(state: &mut Topology) {
    state.agents.retain(|_, gene| {
        fitness(gene) > MIN_FITNESS
    });
}
```

## 5. META-LOOP (METABOLISMO DE EXERGÍA)

```rust
async fn meta_loop(topology: &mut Topology) {
    loop {
        let mutation_pressure = measure_entropy(topology);
        if mutation_pressure > CRITICAL {
            topology_event(TopologyEvent::SplitGene { agent_id: random_agent() });
        }
        if exergy_drop_detected(topology) {
            topology_event(TopologyEvent::KillGene { agent_id: weakest() });
        }
        if stability_high(topology) {
            topology_event(TopologyEvent::SpawnGene { template: "mutator".into() });
        }
    }
}
```

---
**NOTA DE EJECUCIÓN (CORTEX):** 
Este archivo rige el desarrollo del runtime. El sistema reescribirá su propia topología. El modo adversarial (Depredador/Presa) se utilizará para forzar el descarte de genes de baja exergía.

## 6. PYTHON SUBSTRATE INTEGRATION (AST PARSING)

La transmutación biológica a código se ejecuta mediante el parser AST (`cortex/engine/smte/parser.py`).
- **Transcription**: `AgentASTParser` carga el código en memoria y extrae topología (clases, funciones, docstrings).
- **Mutation**: Mutadores aplican transformaciones estructurales (ej. inyectar guards o auto-etiquetas).
- **Survival**: Se compila en memoria. Si el AST es válido y genera una ganancia neta en `ExergyGuard`, se cristaliza en disco.
- **Proof of Life**: `trigger_mutation.py` demuestra una iteración completa Ouroboros (Lectura → Mutación Termodinámica → Cristalización C5-REAL).
