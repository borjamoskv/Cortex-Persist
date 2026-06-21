const http = require('node:http');
const { EventEmitter } = require('node:events');
const { createEnvelope, MESSAGE_TYPES } = require('./protocol');
const { SwarmNeo4jStore } = require('./neo4j');
const { createSwarmBus, makeEnvelope } = require('./bus');

let NeuralNetwork;
try {
  NeuralNetwork = require('brain.js').NeuralNetwork;
} catch {
  NeuralNetwork = null;
}

class BrainNode extends EventEmitter {
  constructor({ id, role, port, coordinatorUrl, neo4j, natsUrl }) {
    super();
    this.id = id;
    this.role = role;
    this.port = port;
    this.coordinatorUrl = coordinatorUrl;
    this.store = new SwarmNeo4jStore(neo4j || {});
    this.server = null;
    this.bus = null;
    this.natsUrl = natsUrl || process.env.NATS_URL || null;
    this.state = {
      id,
      role,
      port,
      status: 'booting',
      load: 0,
      lastHeartbeatAt: null,
      memory: [],
      counters: {},
      topology: {},
    };
    this.prevHash = 'GENESIS';
    this.net = NeuralNetwork ? new NeuralNetwork({ hiddenLayers: [6, 4] }) : null;
    this.commandSubscription = null;
  }

  async init() {
    await this.store.ensureSchema();
    this.train();
    this.bus = await createSwarmBus({ natsUrl: this.natsUrl });
    this.commandSubscription = await this.bus.subscribe('brain.commands', async (command) => {
      try {
        if (command && command.targetNodeId && command.targetNodeId !== this.id) return;
        if (command && command.targetRole && command.targetRole !== this.role) return;
        if (command && command.action) {
          await this.handleEnvelope({
            type: command.action,
            source: command.meta?.source || 'coordinator',
            target: this.id,
            payload: command.payload || {},
            meta: command.meta || {},
            timestamp: command.timestamp || new Date().toISOString(),
            hash: command.hash || null,
            prevHash: command.prevHash || 'GENESIS',
          });
        }
      } catch (error) {
        await this.emit(MESSAGE_TYPES.STATE_CHANGE, { error: error.message, phase: 'command_handler' });
      }
    });
    await this.persistNode();
    return this;
  }

  train() {
    if (!this.net) return;
    const samples = [
      { input: { salience: 0.95, load: 0.1, arousal: 0.9, reward: 0.7 }, output: { route: 1 } },
      { input: { salience: 0.2, load: 0.8, arousal: 0.2, reward: 0.1 }, output: { route: 0 } },
      { input: { salience: 0.75, load: 0.3, arousal: 0.7, reward: 0.6 }, output: { route: 1 } },
      { input: { salience: 0.15, load: 0.2, arousal: 0.3, reward: 0.2 }, output: { route: 0 } },
    ];
    this.net.train(samples, { iterations: 150, errorThresh: 0.01, log: false, learningRate: 0.2 });
  }

  score(payload = {}) {
    if (!this.net) {
      return payload.salience > 0.5 ? 'CEN' : 'DMN';
    }
    const result = this.net.run({
      salience: payload.salience ?? 0,
      load: this.state.load,
      arousal: payload.arousal ?? 0,
      reward: payload.reward ?? 0,
    });
    return result.route >= 0.5 ? 'CEN' : 'DMN';
  }

  async persistNode() {
    await this.store.upsertNode({
      id: this.id,
      role: this.role,
      port: this.port,
      status: this.state.status,
      load: this.state.load,
      updated_at: new Date().toISOString(),
    });
  }

  record(type, payload) {
    const event = createEnvelope({
      type,
      source: this.id,
      target: this.role,
      payload,
      prevHash: this.prevHash,
    });
    this.prevHash = event.hash;
    this.state.memory.push(event);
    this.state.counters[type] = (this.state.counters[type] || 0) + 1;
    return event;
  }

  async emit(type, payload = {}, meta = {}) {
    const envelope = makeEnvelope({
      nodeId: this.id,
      type,
      payload,
      meta: { ...meta, role: this.role },
      prevHash: this.prevHash,
    });
    this.prevHash = envelope.hash;
    this.state.memory.push(envelope);
    await this.store.writeEvent(envelope);
    if (this.bus) {
      await this.bus.publish('brain.events', envelope);
    }
    return envelope;
  }

  async handleEnvelope(envelope) {
    if (!envelope || !envelope.type) {
      throw new Error('Invalid envelope');
    }

    this.state.status = 'active';
    this.state.load = Math.min(1, this.state.load + 0.05);
    this.state.lastHeartbeatAt = new Date().toISOString();

    const event = this.record(envelope.type, envelope.payload);
    await this.store.writeEvent(event);

    let derived = null;
    if ([MESSAGE_TYPES.SPIKE, MESSAGE_TYPES.ATTENTION_SHIFT, MESSAGE_TYPES.REWARD_SIGNAL].includes(envelope.type)) {
      const route = this.score(envelope.payload);
      derived = this.record(MESSAGE_TYPES.ROUTE_DECISION, {
        route,
        confidence: route === 'CEN' ? 0.84 : 0.62,
        derivedFrom: envelope.id,
      });
      await this.store.writeEvent(derived);
      if (this.bus) {
        await this.bus.publish('brain.events', derived);
      }
    }

    await this.persistNode();

    return {
      accepted: true,
      event,
      derived,
      snapshot: this.snapshot(),
    };
  }

  snapshot() {
    return {
      id: this.id,
      role: this.role,
      port: this.port,
      status: this.state.status,
      load: this.state.load,
      counters: this.state.counters,
      lastHeartbeatAt: this.state.lastHeartbeatAt,
      memorySize: this.state.memory.length,
    };
  }

  async heartbeat() {
    this.state.lastHeartbeatAt = new Date().toISOString();
    await this.persistNode();
    if (this.bus) {
      await this.bus.publish('brain.telemetry', {
        type: MESSAGE_TYPES.HEARTBEAT,
        source: this.id,
        target: 'coordinator',
        payload: this.snapshot(),
        timestamp: new Date().toISOString(),
      });
    }
    if (!this.coordinatorUrl) return;

    await fetch(`${this.coordinatorUrl}/heartbeat`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(this.snapshot()),
    }).catch(() => null);
  }

  async register() {
    if (this.bus) {
      await this.bus.publish('brain.telemetry', {
        type: MESSAGE_TYPES.REGISTER,
        source: this.id,
        target: 'coordinator',
        payload: { id: this.id, role: this.role, port: this.port },
        timestamp: new Date().toISOString(),
      });
    }
    if (!this.coordinatorUrl) return;
    await fetch(`${this.coordinatorUrl}/register`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        id: this.id,
        role: this.role,
        port: this.port,
        url: `http://localhost:${this.port}`,
      }),
    }).catch(() => null);
  }

  async start() {
    await this.init();
    await this.register();

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

          if (req.method === 'GET' && req.url === '/snapshot') {
            res.writeHead(200, { 'content-type': 'application/json' });
            res.end(JSON.stringify(this.snapshot()));
            return;
          }

          if (req.method === 'POST' && req.url === '/message') {
            const result = await this.handleEnvelope(body);
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
    this.state.status = 'online';
    await this.persistNode();
    this.heartbeatLoop = setInterval(() => this.heartbeat().catch(() => null), 5000);
    return this;
  }

  async stop() {
    this.state.status = 'offline';
    if (this.heartbeatLoop) clearInterval(this.heartbeatLoop);
    if (this.commandSubscription) {
      try { this.commandSubscription.unsubscribe(); } catch {}
      this.commandSubscription = null;
    }
    await this.persistNode();
    await this.store.close();
    if (this.bus) {
      await this.bus.close().catch(() => null);
    }
    if (this.server) {
      await new Promise((resolve) => this.server.close(resolve));
    }
  }
}

module.exports = { BrainNode };