const net = require('node:net');
const crypto = require('node:crypto');
const { createMessage, MESSAGE_TYPES, NODE_ROLES, encode, safeParse, makeId } = require('./protocol');
const { write } = require('./node');

let Neo4jStore = null;
try {
  ({ Neo4jStore } = require('../../brain-runtime/src/neo4j'));
} catch {
  Neo4jStore = null;
}

function stableStringify(value) {
  const seen = new WeakSet();
  return JSON.stringify(value, function (key, val) {
    if (val && typeof val === 'object') {
      if (seen.has(val)) return '[Circular]';
      seen.add(val);
      if (!Array.isArray(val)) {
        return Object.keys(val)
          .sort()
          .reduce((acc, k) => {
            acc[k] = val[k];
            return acc;
          }, {});
      }
    }
    return val;
  });
}

function sha256(input) {
  return crypto.createHash('sha256').update(input).digest('hex');
}

function connectLineProtocol(socket, onMessage) {
  let buffer = '';
  socket.on('data', (chunk) => {
    buffer += chunk.toString('utf8');
    let idx;
    while ((idx = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 1);
      const message = safeParse(line);
      if (message) onMessage(message);
    }
  });
}

class SwarmCoordinator {
  constructor({ host = '0.0.0.0', port = 5050, heartbeatMs = 5000, nodeTimeoutMs = 15000, neo4j = null } = {}) {
    this.host = host;
    this.port = port;
    this.heartbeatMs = heartbeatMs;
    this.nodeTimeoutMs = nodeTimeoutMs;
    this.server = null;
    this.nodes = new Map();
    this.eventLog = [];
    this.lastHash = 'GENESIS';
    this.store = null;
    this.neo4jConfig = neo4j;
  }

  async init() {
    if (this.neo4jConfig && Neo4jStore) {
      this.store = new Neo4jStore(this.neo4jConfig);
      await this.store.ensureSchema();
    }

    this.server = net.createServer((socket) => this.handleConnection(socket));
    await new Promise((resolve) => this.server.listen(this.port, this.host, resolve));

    this.heartbeatTimer = setInterval(() => this.pulse(), this.heartbeatMs);
    this.reaperTimer = setInterval(() => this.reap(), this.heartbeatMs);

    return this;
  }

  async shutdown() {
    clearInterval(this.heartbeatTimer);
    clearInterval(this.reaperTimer);
    for (const node of this.nodes.values()) {
      try { node.socket.end(); } catch {}
    }
    if (this.server) {
      await new Promise((resolve) => this.server.close(resolve));
    }
    if (this.store) {
      await this.store.close();
    }
  }

  handleConnection(socket) {
    const connection = { socket, nodeId: null };

    connectLineProtocol(socket, (message) => {
      switch (message.type) {
        case MESSAGE_TYPES.REGISTER:
          this.registerNode(connection, message.payload);
          break;
        case MESSAGE_TYPES.HEARTBEAT_ACK:
          this.touchNode(message.payload.nodeId);
          break;
        case MESSAGE_TYPES.TASK_RESULT:
          this.handleTaskResult(message.payload);
          break;
        case MESSAGE_TYPES.EVENT:
          this.receiveEvent(message.payload);
          break;
        case MESSAGE_TYPES.ERROR:
          console.error('[swarm:error]', message.payload);
          break;
        default:
          break;
      }
    });

    socket.on('close', () => {
      if (connection.nodeId && this.nodes.has(connection.nodeId)) {
        this.nodes.delete(connection.nodeId);
      }
    });
  }

  registerNode(connection, payload) {
    const nodeId = payload.id || makeId();
    connection.nodeId = nodeId;
    this.nodes.set(nodeId, {
      id: nodeId,
      role: payload.role,
      capabilities: payload.capabilities || [],
      load: payload.load || 0,
      lastSeenAt: Date.now(),
      socket: connection.socket,
    });

    write(connection.socket, createMessage(MESSAGE_TYPES.REGISTERED, {
      nodeId,
      cluster: 'cortex-persist-swarm',
      roles: Array.from(new Set([...this.nodes.values()].map((n) => n.role))),
    }));
  }

  touchNode(nodeId) {
    const node = this.nodes.get(nodeId);
    if (node) node.lastSeenAt = Date.now();
  }

  reap() {
    const now = Date.now();
    for (const [nodeId, node] of this.nodes.entries()) {
      if (now - node.lastSeenAt > this.nodeTimeoutMs) {
        try { node.socket.end(); } catch {}
        this.nodes.delete(nodeId);
      }
    }
  }

  pulse() {
    for (const node of this.nodes.values()) {
      write(node.socket, createMessage(MESSAGE_TYPES.HEARTBEAT, { nodeId: node.id }));
    }
  }

  appendEvent(event) {
    const canonical = stableStringify(event);
    const entry = {
      id: event.id || makeId(),
      type: event.type,
      timestamp: event.timestamp || new Date().toISOString(),
      payload: event.payload || {},
      meta: event.meta || {},
      prevHash: this.lastHash,
    };
    entry.hash = sha256(`${entry.prevHash}:${canonical}`);
    this.lastHash = entry.hash;
    this.eventLog.push(entry);

    if (this.store) {
      this.store.writeEvent(entry).catch((err) => console.error('[neo4j:event-write]', err.message));
    }

    return entry;
  }

  receiveEvent(event) {
    const entry = this.appendEvent(event);
    const targets = this.route(entry);
    for (const target of targets) {
      this.dispatch(target.role, target.eventType, target.payload, target.meta);
    }
  }

  handleTaskResult(payload) {
    const node = this.nodes.get(payload.nodeId);
    if (node) node.load = Math.max(0, node.load - 1);

    const result = payload.result || {};
    const output = result.output || {};
    const route = output.route;
    if (route) {
      this.dispatch(route, 'ROUTE_DECISION', {
        sourceNode: payload.nodeId,
        sourceTaskId: payload.taskId,
        route,
        confidence: output.confidence ?? output.salienceScore ?? null,
        payload: result.event?.payload || {},
      }, {
        via: payload.nodeId,
        cause: 'task_result_route',
      });
    }
  }

  route(entry) {
    const payload = entry.payload || {};
    const salience = Number(payload.salience ?? payload.salienceScore ?? 0);
    const arousal = Number(payload.arousal ?? 0);

    if (entry.type === 'ATTENTION_SHIFT') {
      return [
        { role: NODE_ROLES.SN, eventType: entry.type, payload, meta: { stage: 'salience_gate' } },
      ];
    }

    if (entry.type === 'SPIKE' || entry.type === 'REWARD_SIGNAL') {
      return [
        { role: NODE_ROLES.SN, eventType: entry.type, payload, meta: { stage: 'salience_gate' } },
        { role: salience > 0.5 || arousal > 0.5 ? NODE_ROLES.CEN : NODE_ROLES.DMN, eventType: entry.type, payload, meta: { stage: 'secondary_route' } },
      ];
    }

    if (entry.type === 'STATE_CHANGE') {
      return [
        { role: NODE_ROLES.MEMORY, eventType: entry.type, payload, meta: { stage: 'state_snapshot' } },
      ];
    }

    return [
      { role: NODE_ROLES.DMN, eventType: entry.type, payload, meta: { stage: 'default' } },
    ];
  }

  selectNode(role) {
    const candidates = [...this.nodes.values()]
      .filter((node) => node.role === role)
      .filter((node) => node.socket && !node.socket.destroyed)
      .sort((a, b) => a.load - b.load || a.lastSeenAt - b.lastSeenAt);

    return candidates[0] || null;
  }

  dispatch(role, eventType, payload = {}, meta = {}) {
    const node = this.selectNode(role);
    if (!node) {
      console.warn(`[swarm:route-drop] No node available for role ${role}`);
      return null;
    }

    node.load += 1;
    const taskId = makeId();
    write(node.socket, createMessage(MESSAGE_TYPES.TASK, {
      taskId,
      role,
      eventType,
      payload,
      meta,
    }));

    return taskId;
  }

  snapshot() {
    return {
      lastHash: this.lastHash,
      nodes: [...this.nodes.values()].map((node) => ({
        id: node.id,
        role: node.role,
        load: node.load,
        lastSeenAt: node.lastSeenAt,
        capabilities: node.capabilities,
      })),
      eventLogLength: this.eventLog.length,
    };
  }
}

module.exports = { SwarmCoordinator };
