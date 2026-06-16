const { BrainRuntime } = require('./brainRuntime');

function env(name, fallback = undefined) {
  return process.env[name] ?? fallback;
}

async function main() {
  const runtime = new BrainRuntime({
    neo4j: {
      uri: env('NEO4J_URI', 'bolt://localhost:7687'),
      username: env('NEO4J_USERNAME', 'neo4j'),
      password: env('NEO4J_PASSWORD', 'neo4j'),
    },
  });

  await runtime.init();

  runtime.bus.on('*', (event) => {
    console.log(JSON.stringify({ kind: 'event', event }, null, 2));
  });

  const isDemo = process.argv.includes('--demo');
  if (isDemo) {
    await runtime.ingest('ATTENTION_SHIFT', {
      salience: 0.91,
      latency: 0.18,
      reward: 0.74,
      arousal: 0.88,
      from_network: 'DMN',
      to_network: 'CEN',
    });

    await runtime.ingest('SPIKE', {
      salience: 0.67,
      latency: 0.3,
      reward: 0.52,
      arousal: 0.64,
      region: 'Amígdala',
      intensity: 0.9,
    });
  }

  process.on('SIGINT', async () => {
    await runtime.shutdown();
    process.exit(0);
  });
}

main().catch(async (err) => {
  console.error(err);
  process.exitCode = 1;
});
