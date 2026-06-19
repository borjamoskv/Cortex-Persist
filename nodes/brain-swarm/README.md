# Brain Swarm

Distributed cognitive OS for Cortex-Persist.

## Topology
- **Coordinator**: routes events, keeps the append-only journal, manages node liveness.
- **SN nodes**: salience gate, decides what deserves oxygen.
- **CEN nodes**: executive execution and planning.
- **DMN nodes**: simulation, reflection, consolidation.
- **MEMORY nodes**: snapshots and compression.
- **MOTOR nodes**: action execution.
- **SENSOR nodes**: ingress and observation.

## Transport
Line-delimited JSON over TCP.

## Run the coordinator
```bash
cd brain-swarm
npm install
npm run coordinator
```

## Run a worker node
```bash
cd brain-swarm
SWARM_ROLE=CEN npm run node
```

## Multi-node example
Terminal 1:
```bash
SWARM_PORT=5050 npm run coordinator
```

Terminal 2:
```bash
SWARM_ROLE=SN SWARM_NODE_ID=sn-1 npm run node
```

Terminal 3:
```bash
SWARM_ROLE=CEN SWARM_NODE_ID=cen-1 npm run node
```

Terminal 4:
```bash
SWARM_ROLE=DMN SWARM_NODE_ID=dmn-1 npm run node
```

## Optional graph persistence
If these env vars exist, the coordinator writes the event log into the Neo4j graph layer:
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=neo4j
```

## Demo mode
```bash
npm run demo
```

This seeds synthetic `ATTENTION_SHIFT`, `SPIKE`, and `REWARD_SIGNAL` events and lets the swarm route them through SN → CEN / DMN / MEMORY.
