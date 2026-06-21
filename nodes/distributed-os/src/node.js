const { randomUUID } = require('node:crypto');
const { BrainRuntime } = require('../../brain-runtime/src/brainRuntime');
const { makeEnvelope } = require('./bus');

class BrainNode {
  constructor({ nodeId, role, graph, bus, version = '0.2.0' }) {
    this.nodeId = nodeId;
    this.role = role;
    this.graph = graph;
    this.bus = bus;
    this.version = version;
    this.runtime = null;
    this.heartbeatTimer = null;
    this.ready = false;
    this.subscriptions = [];
    this.load = 0.1;
    this.queueDepth = 0;
    this.prevHash = 'GENESIS';
  }

  async init() {
    this.runtime = new BrainRuntime({
      neo4j: this.graph.base.config ?? this.graph.base?.config ?? {
        uri: process.env.NEO4J_URI || 'bolt://localhost:7687',
        username: process.env.NEO4J_USERNAME || 'neo4j',
        password: process.env.NEO4J_PASSWORD || 'neo4j',
      },
    });

    await this.graph.ensureSchema();
    await this.graph.upsertAgent({
      nodeId: this.nodeId,
      role: this.role,
      status: 'booting',
      load: this.load,
      version: this.version,
      lastSeenAt: new Date().toISOString(),
    });

    this.subscriptions.push(await this.bus.subscribe('brain.commands', (message) => this.handleCommand(message)));
    this.ready = true;
    this.startHeartbeat();
    await this.emit('NODE_ONLINE', { nodeId: this.nodeId, role: this.role, version: this.version });
    return this;
  }

  startHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    this.heartbeatTimer = setInterval(async () => {
      this.load = Math.min(0.95, Math.max(0.05, this.load + (Math.random() * 0.08 - 0.04)));
      this.queueDepth = Math.max(0, this.queueDepth + (Math.random() > 0.7 ? 1 : -1));
      await this.graph.heartbeat({
        nodeId: this.nodeId,
        role: this.role,
        load: Number(this.load.toFixed(3)),
        queueDepth: this.queueDepth,
        version: this.version,
      });
      await this.emit('NODE_HEARTBEAT', {
        nodeId: this.nodeId,
        role: this.role,
        load: Number(this.load.toFixed(3)),
        queueDepth: this.queueDepth,
      });
    }, 4000);
  }

  async emit(type, payload = {}, meta = {}) {
    const envelope = makeEnvelope({
      nodeId: this.nodeId,
      type,
      payload,
      meta,
      prevHash: this.prevHash,
    });
    this.prevHash = envelope.hash;
    await this.graph.recordEnvelope(envelope);
    await this.bus.publish('brain.events', envelope);
    return envelope;
  }

  acceptCommand(command) {
    if (!command || typeof command !== 'object') return false;
    if (command.targetNodeId && command.targetNodeId !== this.nodeId) return false;
    if (command.targetRole && command.targetRole !== this.role) return false;
    return true;
  }

  async handleCommand(command) {
    if (!this.acceptCommand(command)) return;

    this.queueDepth += 1;
    try {
      switch (command.action) {
        case 'REGISTER_REGION':
          if (command.payload?.regionName) {
            await this.graph.attachAgentToRegion(this.nodeId, command.payload.regionName);
          }
          await this.emit('REGION_ATTACHED', command.payload, { commandId: command.id });
          break;
        case 'PROCESS_IMPULSE':
          await this.processImpulse(command.payload || {}, command.id);
          break;
        case 'SNAPSHOT':
          await this.emit('SNAPSHOT_RECORDED', {
            nodeId: this.nodeId,
            snapshotId: randomUUID(),
            role: this.role,
          }, { commandId: command.id });
          break;
        default:
          await this.emit('COMMAND_IGNORED', {
            nodeId: this.nodeId,
            action: command.action,
          }, { commandId: command.id });
      }
    } finally {
      this.queueDepth = Math.max(0, this.queueDepth - 1);
    }
  }

  routeFromSignal(payload) {
    const salience = Number(payload.salience ?? 0);
    const arousal = Number(payload.arousal ?? 0);
    const reward = Number(payload.reward ?? 0);
    const heat = salience * 0.5 + arousal * 0.3 + reward * 0.2;

    if (this.role === 'SN') {
      return heat > 0.6 ? 'CEN' : 'DMN';
    }

    if (this.role === 'CEN') {
      return heat > 0.45 ? 'EXECUTE' : 'DEFER';
    }

    return heat > 0.3 ? 'SIMULATE' : 'IDLE';
  }

  async processImpulse(payload, commandId) {
    const route = this.routeFromSignal(payload);
    const output = {
      nodeId: this.nodeId,
      role: this.role,
      route,
      salience: payload.salience ?? 0,
      confidence: Math.max(0.1, Math.min(0.99, (payload.salience ?? 0) * 0.7 + 0.2)),
    };

    await this.graph.recordCompletion({
      taskId: payload.taskId || commandId || randomUUID(),
      nodeId: this.nodeId,
      output,
    });

    await this.emit('ROUTE_DECISION', output, { commandId });
  }

  async shutdown() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    for (const sub of this.subscriptions) {
      try { sub.unsubscribe(); } catch {}
    }
    this.subscriptions = [];
    await this.graph.upsertAgent({
      nodeId: this.nodeId,
      role: this.role,
      status: 'offline',
      load: 0,
      version: this.version,
      lastSeenAt: new Date().toISOString(),
    });
  }
}

module.exports = { BrainNode };
