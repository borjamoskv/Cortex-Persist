# Brain Runtime

Executable Node runtime for the C4-SIM brain graph.

## Stack
- Node.js
- brain.js
- Neo4j
- append-only event bus with hash chaining

## Install
```bash
cd brain-runtime
npm install
```

## Configure
```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=neo4j
```

## Run
```bash
npm start
```

## Demo mode
```bash
npm run demo
```

## Behavior
- creates graph constraints
- seeds regions, networks, and neuromodulators
- writes all events to Neo4j
- derives route decisions from attention/salience signals
- uses brain.js when available, with a deterministic fallback path
