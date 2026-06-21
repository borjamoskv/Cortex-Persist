const { BrainNode } = require('./worker');
const { SwarmCoordinator } = require('./coordinator');
const { launchLocalSwarm } = require('./swarm');
const { EVENT_TYPES } = require('./protocol');

function env(name, fallback = undefined) {
  return process.env[name] ?? fallback;
}

async function runCoordinator() {
  const coordinator = new SwarmCoordinator({
    port: env('PORT', 7000),
    neo4j: {
      uri: env('NEO4J_URI'),
      username: env('NEO4J_USERNAME'),
      password: env('NEO4J_PASSWORD'),
    },
  });

  await coordinator.start();
  console.log(`[coordinator] listening on ${env('PORT', 7000)}`);

  process.on('SIGINT', async () => {
    await coordinator.shutdown();
    process.exit(0);
  });
}

async function runNode() {
  const node = new BrainNode({
    role: env('ROLE', 'region'),
    port: env('PORT', 7101),
    host: env('HOST', '127.0.0.1'),
    coordinatorUrl: env('COORDINATOR_URL', 'http://127.0.0.1:7000'),
    neo4j: {
      uri: env('NEO4J_URI'),
      username: env('NEO4J_USERNAME'),
      password: env('NEO4J_PASSWORD'),
    },
  });

  await node.start();
  console.log(`[node:${node.role}] listening on ${node.port}`);

  process.on('SIGINT', async () => {
    await node.shutdown();
    process.exit(0);
  });
}

async function runDemo() {
  const coordinator = new SwarmCoordinator({
    port: 7000,
    neo4j: {
      uri: env('NEO4J_URI'),
      username: env('NEO4J_USERNAME'),
      password: env('NEO4J_PASSWORD'),
    },
  });
  await coordinator.start();

  const dmn = new BrainNode({ role: 'dmn', port: 7101, coordinatorUrl: 'http://127.0.0.1:7000' });
  const cen = new BrainNode({ role: 'cen', port: 7102, coordinatorUrl: 'http://127.0.0.1:7000' });
  const sn = new BrainNode({ role: 'sn', port: 7103, coordinatorUrl: 'http://127.0.0.1:7000' });

  await Promise.all([dmn.start(), cen.start(), sn.start()]);

  await coordinator.ingest({
    type: EVENT_TYPES.ATTENTION_SHIFT,
    payload: { salience: 0.92, reward: 0.71, arousal: 0.88 },
  });
  await coordinator.ingest({
    type: EVENT_TYPES.SPIKE,
    payload: { salience: 0.33, reward: 0.18, arousal: 0.21 },
  });
  await coordinator.ingest({
    type: EVENT_TYPES.REWARD_SIGNAL,
    payload: { salience: 0.51, reward: 0.93, arousal: 0.6 },
  });

  console.log(JSON.stringify(await (await fetch('http://127.0.0.1:7000/topology')).json(), null, 2));
}

async function main() {
  const mode = process.argv[2] ?? env('MODE', 'coordinator');

  if (mode === 'swarm') return launchLocalSwarm();
  if (mode === 'node') return runNode();
  if (mode === 'demo') return runDemo();
  return runCoordinator();
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
