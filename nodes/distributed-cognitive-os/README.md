# Distributed Cognitive OS

Multi-node brain swarm for Cortex-Persist.

## Shape
- Coordinator: global routing, replay, topology
- Nodes: local cognition workers with role-based execution
- Neo4j: graph state + event ledger
- Event log: hash-chained deterministic history

## Roles
- `dmn` idle simulation and counterfactuals
- `cen` focused execution and problem solving
- `sn` salience interrupt and routing switch
- `region` generic micro-region worker

## Run

### 1. Coordinator
```bash
cd distributed-cognitive-os
npm install
NEO4J_URI=bolt://localhost:7687 \
NEO4J_USERNAME=neo4j \
NEO4J_PASSWORD=neo4j \
npm run start:coordinator
```

### 2. Node
```bash
ROLE=cen \
PORT=7102 \
COORDINATOR_URL=http://127.0.0.1:7000 \
NEO4J_URI=bolt://localhost:7687 \
NEO4J_USERNAME=neo4j \
NEO4J_PASSWORD=neo4j \
npm run start:node
```

### 3. Local swarm
```bash
npm run start:swarm
```

### 4. Demo stimulus
```bash
npm run demo
```

## Endpoints
Coordinator:
- `GET /health`
- `GET /topology`
- `GET /events`
- `POST /register`
- `POST /heartbeat`
- `POST /ingest`
- `POST /replay`

Node:
- `GET /health`
- `GET /state`
- `GET /ledger`
- `POST /ingest`
- `POST /sync`

## Routing rule
- high salience -> `sn` + `cen`
- reward-heavy signal -> `cen` + `dmn`
- low-salience spike -> `dmn`
- everything else -> `cen` + `dmn`

## Notes
This scaffold is intentionally transport-light. It runs on plain HTTP first, then can be swapped to Kafka, NATS, or Redis Streams without rewriting the cognitive layer.
