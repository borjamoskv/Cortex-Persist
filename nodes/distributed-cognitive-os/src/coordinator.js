const http = require('node:http');
const crypto = require('node:crypto');
const { Neo4jStore } = require('./neo4jStore');
const { chainEvent } = require('./hash');
const { routePolicy } = require('./protocol');

function readJson(req) {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', (chunk) => {
      raw += chunk;
      if (raw.length > 1_000_000) req.destroy(new Error('payload_too_large'));
    });
    req.on('end', () => {
      if (!raw) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch (err) {
        reject(err);
      }
    });
    req.on('error', reject);
  });
}

function json(res, status, data) {
  res.writeHead(status, { 'content-type': 'application/json' });
  res.end(JSON.stringify(data));
}

function scoreNode(node) {
  const load = Number(node.load ?? 0);
  const ageMs = Math.max(0, Date.now() - new Date(node.lastSeen ?? Date.now()).getTime());
  return load + ageMs / 60000;
}

class SwarmCoordinator {
  constructor(config) {
    this.id = config.id ?? 'coordinator';
    this.host = config.host ?? '0.0.0.0';
    this.port = Number(config.port ?? 7000);
    this.store = new Neo4jStore(config.neo4j ?? {});
    this.nodes = new Map();
    this.ledger = [];
    this.lastHash = 'GENESIS';
    this.server = null;
  }

  async init() {
    await this.store.ensureSchema();
    return this;
  }

  registerNode(node) {
    this.nodes.set(node.id, {
      ...node,
      lastSeen: node.lastSeen ?? new Date().toISOString(),
      status: node.status ?? 'ready',
      load: Number(node.load ?? 0),
    });
  }

  heartbeat(node) {
    const current = this.nodes.get(node.id) ?? {};
    this.nodes.set(node.id, {
      ...current,
      ...node,
      lastSeen: node.lastSeen ?? new Date().toISOString(),
    });
  }

  makeEvent(type, payload = {}, meta = {}) {
    const event = {
      id: crypto.randomUUID(),
      type,
      timestamp: new Date().toISOString(),
      payload,
      meta: { ...meta, origin: this.id },
    };
    event.prevHash = this.lastHash;
    event.hash = chainEvent(this.lastHash, event);
    this.lastHash = event.hash;
    return event;
  }

  async persistEvent(event) {
    this.ledger.push(event);
    await this.store.writeEvent({
      ...event,
      origin: event.meta?.origin ?? this.id,
      route: event.meta?.route ?? null,
    });
  }

  selectNodes(event) {
    const roles = routePolicy(event);
    const candidates = [];
    for (const role of roles) {
      const pool = [...this.nodes.values()].filter((node) => node.role === role && node.status !== 'offline');
      pool.sort((a, b) => scoreNode(a) - scoreNode(b));
      if (pool[0]) candidates.push(pool[0]);
    }
    return candidates;
  }

  async dispatch(node, event) {
    const response = await fetch(`http://${node.host}:${node.port}/ingest`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ event }),
    });
    const body = await response.json().catch(() => ({}));
    return { status: response.status, body, node };
  }

  async ingest(event) {
    const normalized = event.id ? event : this.makeEvent(event.type, event.payload ?? {}, event.meta ?? {});
    const targets = this.selectNodes(normalized);
    const route = targets.map((node) => node.role);
    normalized.meta = { ...normalized.meta, route };

    await this.persistEvent(normalized);

    const results = [];
    for (const node of targets) {
      try {
        const result = await this.dispatch(node, normalized);
        results.push(result);
        await this.store.linkEventToNode(normalized.id, node.id).catch(() => null);
      } catch (err) {
        results.push({ node, error: err.message });
      }
    }

    return { accepted: true, event: normalized, route, results };
  }

  snapshot() {
    return {
      nodes: [...this.nodes.values()],
      ledger: this.ledger,
      size: this.ledger.length,
    };
  }

  async start() {
    await this.init();
    this.server = http.createServer(async (req, res) => {
      const url = new URL(req.url, `http://${req.headers.host}`);

      try {
        if (req.method === 'GET' && url.pathname === '/health') {
          return json(res, 200, { ok: true, id: this.id, nodes: this.nodes.size, events: this.ledger.length });
        }

        if (req.method === 'GET' && url.pathname === '/topology') {
          return json(res, 200, this.snapshot());
        }

        if (req.method === 'GET' && url.pathname === '/events') {
          return json(res, 200, { ledger: this.ledger });
        }

        if (req.method === 'POST' && url.pathname === '/register') {
          const body = await readJson(req);
          this.registerNode(body);
          await this.store.upsertNode(body).catch(() => null);
          return json(res, 200, { ok: true, registered: body.id });
        }

        if (req.method === 'POST' && url.pathname === '/heartbeat') {
          const body = await readJson(req);
          this.heartbeat(body);
          await this.store.upsertNode(body).catch(() => null);
          return json(res, 200, { ok: true });
        }

        if (req.method === 'POST' && url.pathname === '/ingest') {
          const body = await readJson(req);
          const event = body.event?.type ? body.event : body;
          const result = await this.ingest(event);
          return json(res, 200, result);
        }

        if (req.method === 'POST' && url.pathname === '/replay') {
          const body = await readJson(req);
          const targetId = body.nodeId;
          const node = [...this.nodes.values()].find((n) => n.id === targetId);
          if (!node) return json(res, 404, { error: 'node_not_found' });
          const response = await fetch(`http://${node.host}:${node.port}/sync`, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ events: this.ledger }),
          });
          const result = await response.json().catch(() => ({}));
          return json(res, 200, { ok: true, replayed: this.ledger.length, result });
        }

        return json(res, 404, { error: 'not_found' });
      } catch (err) {
        return json(res, 500, { error: err.message });
      }
    });

    await new Promise((resolve) => this.server.listen(this.port, this.host, resolve));
    return this;
  }

  async shutdown() {
    if (this.server) await new Promise((resolve) => this.server.close(resolve));
    await this.store.close();
  }
}

module.exports = { SwarmCoordinator };
