const http = require('node:http');
const { createEnvelope, MESSAGE_TYPES } = require('./protocol');
const { SwarmNeo4jStore } = require('./neo4j');
const { createSwarmBus, makeEnvelope } = require('./bus');

class SwarmCoordinator {
  constructor({ port, neo4j, natsUrl }) {
    this.port = port;
    this.store = new SwarmNeo4jStore(neo4j || {});
    this.server = null;
    this.nodes = new Map();
    this.eventLog = [];
    this.prevHash = 'GENESIS';
    this.bus = null;
    this.natsUrl = natsUrl || process.env.NATS_URL || null;
    this.subscriptions = [];
  }

  async init() {
    await this.store.ensureSchema();
    this.bus = await createSwarmBus({ natsUrl: this.natsUrl });
    this.subscriptions.push(await this.bus.subscribe('brain.telemetry', (msg) => this.observeTelemetry(msg)));
    this.subscriptions.push(await this.bus.subscribe('brain.events', (msg) => this.observeEvent(msg)));
    return this;
  }

  record(type, payload, source = 'coordinator', target = 'swarm') {
    const event = createEnvelope({
      type,
      source,
      target,
      payload,
      prevHash: this.prevHash,
    });
    this.prevHash = event.hash;
    this.eventLog.push(event);
    return event;
  }

  async persistNode(node) {
    await this.store.upsertNode({
      id: node.id,
      role: node.role,
      port: node.port,
      status: node.status || 'online',
      load: node.load ?? 0,
      updated_at: new Date().toISOString(),
    });
  }

  registerNode(node) {
    this.nodes.set(node.id, {
      id: node.id,
      role: node.role,
      port: node.port,
      url: node.url || `http://localhost:${node.port}`,
      status: 'online',
      load: 0,
      queueDepth: 0,
      lastHeartbeatAt: new Date().toISOString(),
    });
    return this.nodes.get(node.id);
  }

  heartbeat(snapshot) {
    const node = this.nodes.get(snapshot.id);
    if (!node) return null;
    Object.assign(node, snapshot, { url: node.url });
    node.lastHeartbeatAt = new Date().toISOString();
    return node;
  }

  observeTelemetry(message) {
    if (!message) return;
    const payload = message.payload || message;
    if (message.type === MESSAGE_TYPES.REGISTER || message.type === 'REGISTER') {
      const node = this.registerNode({
        id: payload.id,
        role: payload.role,
        port: payload.port,
        url: payload.url,
      });
      this.persistNode(node).catch(() => null);
      return;
    }

    if (message.type === MESSAGE_TYPES.HEARTBEAT || message.type === 'HEARTBEAT') {
      const node = this.heartbeat({
        id: payload.id,
        role: payload.role,
        port: payload.port,
        load: payload.load ?? 0,
        queueDepth: payload.queueDepth ?? 0,
        status: payload.status || 'online',
      });
      if (node) this.persistNode(node).catch(() => null);
    }
  }

  observeEvent(event) {
    if (!event || !event.type) return;
    this.eventLog.push(event);
    if (event.type === MESSAGE_TYPES.ROUTE_DECISION) {
      const p = event.payload || {};
      const node = p.nodeId ? this.nodes.get(p.nodeId) : null;
      if (node) {
        node.load = Math.min(1, Math.max(0, (node.load || 0) * 0.92 + 0.04));
        node.lastHeartbeatAt = event.timestamp;
        this.persistNode(node).catch(() => null);
      }
    }
  }

  selectNode(type, payload = {}) {
    const candidates = [...this.nodes.values()].filter((n) => n.status !== 'offline');
    if (!candidates.length) return null;

    const desiredRole = type === MESSAGE_TYPES.ATTENTION_SHIFT || type === MESSAGE_TYPES.REWARD_SIGNAL
      ? 'CEN'
      : type === MESSAGE_TYPES.SPIKE
        ? 'SN'
        : 'DMN';

    const scored = candidates.map((node) => {
      const roleBoost = node.role === desiredRole ? 1 : 0;
      const loadPenalty = node.load || 0;
      const latencyHint = payload.latency ?? 0;
      const queuePenalty = (node.queueDepth || 0) * 0.1;
      return {
        node,
        score: roleBoost * 2 - loadPenalty - latencyHint * 0.1 - queuePenalty,
      };
    });

    scored.sort((a, b) => b.score - a.score);
    return scored[0].node;
  }

  async dispatch(type, payload = {}, meta = {}) {
    const node = this.selectNode(type, payload);
    if (!node) {
      throw new Error('No online nodes available');
    }

    const event = this.record(type, payload, 'coordinator', node.id);
    await this.store.writeEvent(event);

    const command = makeEnvelope({
      nodeId: 'coordinator',
      type: 'COMMAND',
      payload: {
        action: type,
        ...payload,
        targetNodeId: node.id,
        targetRole: node.role,
      },
      meta: { ...meta, routedBy: 'coordinator', targetNode: node.id },
      prevHash: this.prevHash,
    });
    this.prevHash = command.hash;
    await this.store.writeEvent(command);
    this.eventLog.push(command);

    if (this.bus) {
      await this.bus.publish('brain.commands', command.payload);
    } else if (node.url) {
      await postJSON(`${node.url}/message`, {
        ...event,
        meta: { ...meta, routedBy: 'coordinator', targetNode: node.id },
      });
    }

    const updated = this.nodes.get(node.id);
    if (updated) {
      updated.load = Math.min(1, (updated.load || 0) + 0.03);
      await this.persistNode(updated);
    }

    return { node, event, command };
  }

  snapshot() {
    return {
      nodes: [...this.nodes.values()],
      eventCount: this.eventLog.length,
      lastHash: this.prevHash,
      bus: Boolean(this.bus),
    };
  }

  async start() {
    await this.init();

    this.server = http.createServer(async (req, res) => {
      const chunks = [];
      req.on('data', (chunk) => chunks.push(chunk));
      req.on('end', async () => {
        try {
          const body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {};

          if (req.method === 'GET' && req.url === '/health') {
            res.writeHead(200, { 'content-type': 'application/json' });
            res.end(JSON.stringify({ ok: true, ...this.snapshot() }));
            return;
          }

          if (req.method === 'GET' && req.url === '/topology') {
            res.writeHead(200, { 'content-type': 'application/json' });
            res.end(JSON.stringify(this.snapshot()));
            return;
          }

          if (req.method === 'POST' && req.url === '/register') {
            const node = this.registerNode(body);
            await this.persistNode(node);
            res.writeHead(200, { 'content-type': 'application/json' });
            res.end(JSON.stringify({ ok: true, node }));
            return;
          }

          if (req.method === 'POST' && req.url === '/heartbeat') {
            const node = this.heartbeat(body);
            if (node) await this.persistNode(node);
            res.writeHead(200, { 'content-type': 'application/json' });
            res.end(JSON.stringify({ ok: true, node }));
            return;
          }

          if (req.method === 'POST' && req.url === '/dispatch') {
            const result = await this.dispatch(body.type, body.payload || {}, body.meta || {});
            res.writeHead(200, { 'content-type': 'application/json' });
            res.end(JSON.stringify(result));
            return;
          }

          if (req.method === 'POST' && req.url === '/shutdown') {
            res.writeHead(200, { 'content-type': 'application/json' });
            res.end(JSON.stringify({ ok: true }));
            await this.stop();
            return;
          }

          res.writeHead(404, { 'content-type': 'application/json' });
          res.end(JSON.stringify({ error: 'not_found' }));
        } catch (error) {
          res.writeHead(500, { 'content-type': 'application/json' });
          res.end(JSON.stringify({ error: error.message }));
        }
      });
    });

    await new Promise((resolve) => this.server.listen(this.port, resolve));
    return this;
  }

  async stop() {
    for (const node of this.nodes.values()) {
      node.status = 'offline';
      await this.persistNode(node);
    }
    for (const sub of this.subscriptions) {
      try { sub.unsubscribe(); } catch {}
    }
    this.subscriptions = [];
    await this.store.close();
    if (this.bus) {
      await this.bus.close().catch(() => null);
    }
    if (this.server) {
      await new Promise((resolve) => this.server.close(resolve));
    }
  }
}

async function postJSON(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  return response.json();
}

module.exports = { SwarmCoordinator };