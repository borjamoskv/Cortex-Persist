# Distributed Cognitive OS

A multi-node brain swarm for the C4-SIM graph. Each node acts as a cognitive worker, the coordinator routes impulses, and Neo4j persists topology plus event history.

## Components
- Coordinator: global routing and swarm state
- Brain nodes: local cognition, event handling, route decisions
- Protocol: hash-chained envelopes
- Neo4j: persistence for nodes, events, snapshots

## Run

### Coordinator
```bash
cd distributed-os
npm install
COORDINATOR_PORT=4010 npm run start:coordinator
```

### Node
```bash
cd distributed-os
NODE_ID=cen-01 NODE_ROLE=CEN NODE_PORT=4022 COORDINATOR_URL=http://localhost:4010 npm run start:node
```

### Demo swarm
```bash
cd distributed-os
npm run demo
```

## Environment
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=neo4j
```

## Message flow
1. Node registers with coordinator.
2. Coordinator tracks heartbeat and load.
3. Incoming events are routed to the best node by role and load.
4. Nodes persist event hashes and emit derived `ROUTE_DECISION` events.
5. Neo4j stores swarm topology and event traces.

## Cognitive roles
- DMN: idle simulation, contextual memory, background synthesis
- CEN: focused execution, task solving, deliberate routing
- SN: salience interception, state switching, interruption control

## Next upgrades
- replace HTTP transport with NATS or Kafka
- add snapshot replication and deterministic replay
- split nodes into worker pools per brain region
- add consensus on route decisions
