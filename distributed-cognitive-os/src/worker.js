const http = require('node:http');
const crypto = require('node:crypto');
const { EventEmitter } = require('node:events');
const { chainEvent } = require('./hash');
const { Neo4jStore } = require('./neo4jStore');
const { EVENT_TYPES } = require('./protocol');

let NeuralNetwork;
try {
  NeuralNetwork = require('brain.js').NeuralNetwork;
} catch {
  NeuralNetwork = null;
}

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

class BrainNode {
  constructor(config) {
    this.id = config.id ?? crypto.randomUUID();
    this.role = config.role;
    this.host = config.host ?? '127.0.0.1';
    this.port = Number(config.port);
    this.coordinatorUrl = config.coordinatorUrl;
    this.capabilities = config.capabilities ?? [this.role];
    this.store = new Neo4jStore(config.neo4j ?? {});
    this.bus = new EventEmitter();
    this.ledger = [];
    this.lastHash = 'GENESIS';
    this.load = 0;
    this.status = 'booting';
    this.currentRoute = null;
    this.net = NeuralNetwork ? new NeuralNetwork({ hiddenLayers: [8, 4] }) : null;
    this.server = null;
    this.heartbeatTimer = null;
  }

  async init() {
    await this.store.ensureSchema();
    this.seedModel();
    this.status = 'ready';
    return this;
  }

  seedModel() {
    if (!this.net) return;
    this.net.train([
      { input: { salience: 0.95, reward: 0.6, arousal: 0.9 }, output: { cen: 1 } },
      { input: { salience: 0.15, reward: 0.2, arousal: 0.2 }, output: { dmn: 1 } },
      { input: { salience: 0.85, reward: 0.8, arousal: 0.7 }, output: { cen: 1 } },
      { input: { salience: 0.35, reward: 0.3, arousal: 0.4 }, output: { dmn: 1 } },
    ], { iterations: 150, errorThresh: 0.01, log: false, learningRate: 0.2 });
  }

  computeRoute(payload = {}) {
    if (!this.net) {
      return payload.salience >= 0.5 ? 'CEN' : 'DMN';
    }
    const out = this.net.run({
      salience: Number(payload.salience ?? 0),
      reward: Number(payload.reward ?? 0),
      arousal: Number(payload.arousal ?? 0),
    });
    return (out.cen ?? 0) >= (out.dmn ?? 0) ? 'CEN' : 'DMN';
  }

  makeEvent(type, payload = {}, meta = {}) {
    const base = {
      id: crypto.randomUUID(),
      type,
      timestamp: new Date().toISOString(),
      payload,
      meta: { ...meta, origin: this.id, role: this.role },
    };
    base.prevHash = this.lastHash;
    base.hash = chainEvent(this.lastHash, base);
    this.lastHash = base.hash;
    return base;
  }

  async persistEvent(event) {
    this.ledger.push(event);
    await this.store.writeEvent({
      ...event,
      route: event.meta?.route ?? null,
      origin: event.meta?.origin ?? this.id,
    });
  }

  applyEvent(event) {
    if (event.type === EVENT_TYPES.ROUTE_DECISION) {
      this.currentRoute = event.payload?.route ?? this.currentRoute;
    }
    if (event.type === EVENT_TYPES.ATTENTION_SHIFT) {
      this.load = Math.min(1, this.load + 0.15);
    } else if (event.type === EVENT_TYPES.SPIKE) {
      this.load = Math.min(1, this.load + 0.1);
    } else if (event.type === EVENT_TYPES.REWARD_SIGNAL) {
      this.load = Math.max(0, this.load - 0.05);
    }
    this.bus.emit(event.type, event);
    this.bus.emit('*', event);
  }

  async ingest(event) {
    const routed = event.type === EVENT_TYPES.ROUTE_DECISION
      ? event
      : (event.type === EVENT_TYPES.ATTENTION_SHIFT || event.type === EVENT_TYPES.SPIKE || event.type === EVENT_TYPES.REWARD_SIGNAL)
        ? this.makeEvent(EVENT_TYPES.ROUTE_DECISION, {
            route: this.computeRoute(event.payload),
            confidence: 0.75,
            sourceEvent: event.id,
          }, { derivedFrom: event.id })
        : null;

    await this.persistEvent(event);
    this.applyEvent(event);

    if (routed) {
      await this.persistEvent(routed);
      this.applyEvent(routed);
    }

    return { accepted: true, nodeId: this.id, event, routed };
  }

  async register() {
    if (!this.coordinatorUrl) return;
    await fetch(`${this.coordinatorUrl}/register`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        id: this.id,
        role: this.role,
        host: this.host,
        port: this.port,
        status: this.status,
        load: this.load,
        capabilities: this.capabilities,
      }),
    });
  }

  async heartbeat() {
    if (!this.coordinatorUrl) return;
    await fetch(`${this.coordinatorUrl}/heartbeat`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        id: this.id,
        role: this.role,
        host: this.host,
        port: this.port,
        status: this.status,
        load: this.load,
        lastSeen: new Date().toISOString(),
        currentRoute: this.currentRoute,
      }),
    }).catch(() => null);
  }

  async start() {
    await this.init();
    this.server = http.createServer(async (req, res) => {
      const url = new URL(req.url, `http://${req.headers.host}`);

      try {
        if (req.method === 'GET' && url.pathname === '/health') {
          return json(res, 200, { ok: true, id: this.id, role: this.role, status: this.status });
        }

        if (req.method === 'GET' && url.pathname === '/state') {
          return json(res, 200, {
            id: this.id,
            role: this.role,
            status: this.status,
            load: this.load,
            route: this.currentRoute,
            events: this.ledger.length,
          });
        }

        if (req.method === 'GET' && url.pathname === '/ledger') {
          return json(res, 200, { id: this.id, ledger: this.ledger });
        }

        if (req.method === 'POST' && url.pathname === '/ingest') {
          const body = await readJson(req);
          const event = body.event?.type ? body.event : body;
          const normalized = event.id ? event : this.makeEvent(event.type, event.payload ?? {}, event.meta ?? {});
          const result = await this.ingest(normalized);
          return json(res, 200, result);
        }

        if (req.method === 'POST' && url.pathname === '/sync') {
          const body = await readJson(req);
          const events = Array.isArray(body.events) ? body.events : [];
          for (const event of events) await this.ingest(event);
          return json(res, 200, { ok: true, synced: events.length });
        }

        return json(res, 404, { error: 'not_found' });
      } catch (err) {
        return json(res, 500, { error: err.message });
      }
    });

    await new Promise((resolve) => this.server.listen(this.port, this.host, resolve));
    await this.register();
    this.heartbeatTimer = setInterval(() => this.heartbeat(), 2000);
    this.heartbeatTimer.unref?.();
    return this;
  }

  async shutdown() {
    this.status = 'stopping';
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    if (this.server) await new Promise((resolve) => this.server.close(resolve));
    await this.store.close();
  }
}

module.exports = { BrainNode };
