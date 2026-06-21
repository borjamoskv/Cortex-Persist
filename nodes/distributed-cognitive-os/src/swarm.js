const { fork } = require('node:child_process');
const path = require('node:path');

function spawnProcess(entry, env) {
  return fork(path.join(__dirname, entry), [], {
    env: { ...process.env, ...env },
    stdio: 'inherit',
  });
}

function launchLocalSwarm({ coordinatorPort = 7000, basePort = 7101 } = {}) {
  const coordinator = spawnProcess('index.js', {
    MODE: 'coordinator',
    PORT: String(coordinatorPort),
  });

  const nodes = [
    { role: 'dmn', port: basePort + 0 },
    { role: 'cen', port: basePort + 1 },
    { role: 'sn', port: basePort + 2 },
    { role: 'region', port: basePort + 3 },
  ].map((node) =>
    spawnProcess('index.js', {
      MODE: 'node',
      ROLE: node.role,
      PORT: String(node.port),
      COORDINATOR_URL: `http://127.0.0.1:${coordinatorPort}`,
    })
  );

  const shutdown = () => {
    for (const child of [coordinator, ...nodes]) {
      try {
        child.kill('SIGINT');
      } catch {}
    }
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  return { coordinator, nodes, shutdown };
}

module.exports = { launchLocalSwarm };
