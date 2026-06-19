const { BrainNode } = require('./nodeAgent');
const { SwarmCoordinator } = require('./coordinator');

function env(name, fallback) {
  return process.env[name] ?? fallback;
}

async function startCoordinator() {
  const coordinator = new SwarmCoordinator({
    port: Number(env('COORDINATOR_PORT', 4010)),
    neo4j: {
      uri: env('NEO4J_URI', 'bolt://localhost:7687'),
      username: env('NEO4J_USERNAME', 'neo4j'),
      password: env('NEO4J_PASSWORD', 'neo4j'),
    },
  });

  await coordinator.start();
  console.log(`coordinator online on ${coordinator.port}`);
  return coordinator;
}

async function startNode() {
  const node = new BrainNode({
    id: env('NODE_ID', `node-${Math.random().toString(36).slice(2, 8)}`),
    role: env('NODE_ROLE', 'DMN'),
    port: Number(env('NODE_PORT', 4020)),
    coordinatorUrl: env('COORDINATOR_URL', 'http://localhost:4010'),
    neo4j: {
      uri: env('NEO4J_URI', 'bolt://localhost:7687'),
      username: env('NEO4J_USERNAME', 'neo4j'),
      password: env('NEO4J_PASSWORD', 'neo4j'),
    },
  });

  await node.start();
  console.log(`node ${node.id} online on ${node.port}`);
  return node;
}

async function demo() {
  const coordinator = await startCoordinator();
  const nodeA = await new BrainNode({
    id: 'dmn-01',
    role: 'DMN',
    port: 4021,
    coordinatorUrl: 'http://localhost:4010',
    neo4j: {
      uri: env('NEO4J_URI', 'bolt://localhost:7687'),
      username: env('NEO4J_USERNAME', 'neo4j'),
      password: env('NEO4J_PASSWORD', 'neo4j'),
    },
  }).start();
  const nodeB = await new BrainNode({
    id: 'cen-01',
    role: 'CEN',
    port: 4022,
    coordinatorUrl: 'http://localhost:4010',
    neo4j: {
      uri: env('NEO4J_URI', 'bolt://localhost:7687'),
      username: env('NEO4J_USERNAME', 'neo4j'),
      password: env('NEO4J_PASSWORD', 'neo4j'),
    },
  }).start();

  await new Promise((r) => setTimeout(r, 1000));
  const result = await coordinator.dispatch('ATTENTION_SHIFT', {
    salience: 0.93,
    latency: 0.22,
    reward: 0.77,
    arousal: 0.89,
    from_network: 'DMN',
    to_network: 'CEN',
  });

  console.log(JSON.stringify({ demo: true, routedTo: result.node.id, snapshot: coordinator.snapshot() }, null, 2));

  process.on('SIGINT', async () => {
    await nodeA.stop();
    await nodeB.stop();
    await coordinator.stop();
    process.exit(0);
  });
}

async function main() {
  const mode = process.argv[2] || 'coordinator';

  if (mode === 'coordinator') return startCoordinator();
  if (mode === 'node') return startNode();
  if (mode === 'demo') return demo();

  throw new Error(`Unknown mode: ${mode}`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
