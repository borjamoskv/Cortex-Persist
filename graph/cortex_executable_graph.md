# Cortex-Persist — Graph Executable Brain (C4-SIM)

## 1. Neo4j Graph Schema (Executable Core)

### Nodes
(:BrainRegion {
  name,
  layer,        // L1-L4
  function,
  latency_ms,
  compute_model
})

(:FunctionalNetwork {
  name,         // DMN | CEN | SN
  frequency_hz,
  state
})

(:Neuromodulator {
  name,
  source,
  effect
})

(:Event {
  id,
  type,         // SPIKE | STATE_CHANGE | ROUTE | REWARD
  timestamp,
  payload
})

---

### Relationships

(:BrainRegion)-[:CONNECTS_TO {latency_ms}]->(:BrainRegion)
(:BrainRegion)-[:PART_OF]->(:FunctionalNetwork)
(:Neuromodulator)-[:MODULATES {gain}]->(:BrainRegion)
(:Event)-[:TARGETS]->(:BrainRegion)
(:Event)-[:TRIGGERS]->(:Event)
(:BrainRegion)-[:ROUTES_TO]->(:BrainRegion)

---

## 2. Event-Sourced Brain Kernel

### Event Types
```yaml
SPIKE:
  fields: [region, intensity, timestamp]

STATE_CHANGE:
  fields: [region, old_state, new_state]

ATTENTION_SHIFT:
  fields: [from_network, to_network, salience_score]

REWARD_SIGNAL:
  fields: [region, dopamine_delta, prediction_error]

ROUTE_DECISION:
  fields: [thalamus_state, selected_path]
```

### Event Store Contract
- Append-only log
- Deterministic replay required
- Hash-chained events (C4-SIM integrity layer)

---

## 3. RDF / Turtle Ontology (Semantic Layer)

```turtle
@prefix brain: <http://cortex.persist/brain#> .

brain:Amigdala a brain:BrainRegion ;
  brain:function "Threat detection IDS" ;
  brain:layer "L2" ;
  brain:computes "salience scoring" .

brain:Hipocampo a brain:BrainRegion ;
  brain:function "episodic memory index" ;
  brain:layer "L2" ;
  brain:computes "vector storage + commit log" .

brain:DMN a brain:FunctionalNetwork ;
  brain:state "idle_simulation" ;
  brain:frequency "alpha" .
```

---

## 4. Execution Semantics

- Graph = runtime brain simulator
- Events = neural impulses
- Edges = synaptic routing paths
- Nodes = computational microservices

### Deterministic Replay Rule
```
state_t+1 = f(state_t, Event_t, neuromodulators_t)
```

---

## 5. Mapping Rules (C4-SIM → Graph)

| Cortex Layer | Graph Representation |
|--------------|---------------------|
| L1 Motor     | real-time node cluster |
| L2 Limbic    | event filters + scoring |
| L3 Routing   | graph traversal engine |
| L4 Cortex    | LLM + feature extraction nodes |

---

## 6. Execution Targets

- Neo4j (primary runtime)
- RDF store (semantic mirror)
- Event-sourced replay engine (deterministic cognition)

---

## 7. Next Step Hooks

- /sim/replay
- /graph/optimize-routing
- /neuro-modulator/tune-dopamine
- /dmn/collapse-cycle
