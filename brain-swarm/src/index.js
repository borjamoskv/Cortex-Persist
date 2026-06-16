const { BrainNode } = require('./node');
const { SwarmCoordinator } = require('./coordinator');
const { NODE_ROLES } = require('./protocol');

function env(name, fallback = undefined) {
  return process.env[name] ?? fallback;
}

function parseArgs(argv) {
  const args = new Set(argv.slice(2));
  return {
    mode: args.has('coordinator') ? 'coordinator' : args.has('node') ? 'node' : env('SWARM_MODE', 'coordinator'),
    demo: args.has('--demo'),
  };
}

async function startCoordinator({ demo }) {
  const coordinator = new SwarmCoordinator({
    host: env('SWARM_HOST', '0.0.0.0'),
    port: Number(env('SWARM_PORT', '5050')),
    heartbeatMs: Number(env('SWARM_HEARTBEAT_MS', '5000')),
    nodeTimeoutMs: Number(env('SWARM_NODE_TIMEOUT_MS', '15000')),
    neo4j: env('NEO4J_URI')
      ? {
          uri: env('NEO4J_URI'),
          username: env('NEO4J_USERNAME', 'neo4j'),
          password: env('NEO4J_PASSWORD', 'neo4j'),
        }
      : null,
  });

  await coordinator.init();
  console.log(`[swarm] coordinator online on ${coordinator.host}:${coordinator.port}`);

  if (demo) {
    const demoEvents = [
      { type: 'ATTENTION_SHIFT', payload: { salience: 0.91, arousal: 0.88, reward: 0.72, latency: 0.18 } },
      { type: 'SPIKE', payload: { salience: 0.64, arousal: 0.55, reward: 0.48, latency: 0.3 } },
      { type: 'REWARD_SIGNAL', payload: { salience: 0.52, arousal: 0.33, reward: 0.9, latency: 0.22 } },
    ];

    for (const event of demoEvents) {
      coordinator.receiveEvent({
        id: event.type,
        type: event.type,
        timestamp: new Date().toISOString(),
        payload: event.payload,
        meta: { source: 'demo' },
      });
    }
  }

  process.on('SIGINT', async () => {
    await coordinator.shutdown();
    process.exit(0);
  });
}

async function startNode() {
  const role = env('SWARM_ROLE', NODE_ROLES.CEN);
  const node = new BrainNode({
    id: env('SWARM_NODE_ID', `${role.toLowerCase()}-${Math.random().toString(16).slice(2, 8)}`),
    role,
    coordinatorHost: env('SWARM_COORDINATOR_HOST', '127.0.0.1'),
    coordinatorPort: Number(env('SWARM_COORDINATOR_PORT', '5050')),
    capabilities: (env('SWARM_CAPABILITIES', '') || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean),
  });

  await node.connect();
  console.log(`[swarm] node ${node.id} online as ${role}`);

  process.on('SIGINT', () => {
    if (node.socket) node.socket.end();
    process.exit(0);
  });
}

async function main() {
  const { mode, demo } = parseArgs(process.argv);

  if (mode === 'node') {
    await startNode();
  } else {
    await startCoordinator({ demo });
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
