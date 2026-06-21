const net = require('node:net');
const { createMessage, MESSAGE_TYPES, NODE_ROLES, encode, safeParse } = require('./protocol');

let NeuralNetwork = null;
try {
  NeuralNetwork = require('brain.js').NeuralNetwork;
} catch {
  NeuralNetwork = null;
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

function write(socket, message) {
  socket.write(encode(message));
}

function createBrainModel(role) {
  if (!NeuralNetwork) return null;
  if (role !== NODE_ROLES.CEN) return null;
  const net = new NeuralNetwork({ hiddenLayers: [6, 4] });
  net.train(
    [
      { input: { salience: 0.95, arousal: 0.9, reward: 0.6, latency: 0.2 }, output: { plan: 1 } },
      { input: { salience: 0.25, arousal: 0.2, reward: 0.2, latency: 0.7 }, output: { plan: 0 } },
      { input: { salience: 0.75, arousal: 0.8, reward: 0.7, latency: 0.3 }, output: { plan: 1 } },
      { input: { salience: 0.1, arousal: 0.1, reward: 0.1, latency: 0.9 }, output: { plan: 0 } },
    ],
    { iterations: 120, errorThresh: 0.01, log: false, learningRate: 0.2 }
  );
  return net;
}

class BrainNode {
  constructor({ id, role, coordinatorHost, coordinatorPort, capabilities = [] }) {
    this.id = id;
    this.role = role;
    this.coordinatorHost = coordinatorHost;
    this.coordinatorPort = coordinatorPort;
    this.capabilities = capabilities;
    this.socket = null;
    this.inflight = 0;
    this.lastHeartbeatAt = null;
    this.model = createBrainModel(role);
    this.localEvents = [];
  }

  connect() {
    return new Promise((resolve, reject) => {
      const socket = net.createConnection({ host: this.coordinatorHost, port: this.coordinatorPort }, () => {
        this.socket = socket;
        write(socket, createMessage(MESSAGE_TYPES.REGISTER, {
          id: this.id,
          role: this.role,
          capabilities: this.capabilities,
          load: this.inflight,
        }));
        resolve();
      });

      socket.on('error', reject);
      connectLineProtocol(socket, (message) => this.handleMessage(message));

      socket.on('close', () => {
        this.socket = null;
      });
    });
  }

  handleMessage(message) {
    switch (message.type) {
      case MESSAGE_TYPES.HEARTBEAT:
        this.lastHeartbeatAt = Date.now();
        if (this.socket) write(this.socket, createMessage(MESSAGE_TYPES.HEARTBEAT_ACK, { nodeId: this.id }));
        break;

      case MESSAGE_TYPES.TASK:
        this.executeTask(message.payload)
          .then((result) => {
            this.localEvents.push(result.event);
            if (this.socket) {
              write(this.socket, createMessage(MESSAGE_TYPES.TASK_RESULT, {
                nodeId: this.id,
                taskId: message.payload.taskId,
                result,
              }));
            }
          })
          .catch((error) => {
            if (this.socket) {
              write(this.socket, createMessage(MESSAGE_TYPES.ERROR, {
                nodeId: this.id,
                taskId: message.payload.taskId,
                error: error.message,
              }));
            }
          });
        break;

      case MESSAGE_TYPES.SYNC:
        if (Array.isArray(message.payload.events)) {
          this.localEvents.push(...message.payload.events);
        }
        break;

      case MESSAGE_TYPES.SHUTDOWN:
        if (this.socket) this.socket.end();
        break;

      default:
        break;
    }
  }

  async executeTask(task) {
    this.inflight += 1;
    try {
      const event = {
        id: task.taskId,
        type: task.eventType || 'TASK_EXECUTION',
        timestamp: new Date().toISOString(),
        payload: task.payload,
        nodeId: this.id,
        role: this.role,
      };

      let output = {};
      if (this.role === NODE_ROLES.SN) {
        const salience = Number(task.payload?.salience ?? 0);
        const arousal = Number(task.payload?.arousal ?? 0);
        const score = Math.min(1, salience * 0.7 + arousal * 0.3);
        output = {
          salienceScore: score,
          route: score >= 0.5 ? NODE_ROLES.CEN : NODE_ROLES.DMN,
          explanation: 'salience gate computed by SN',
        };
      } else if (this.role === NODE_ROLES.CEN) {
        const input = {
          salience: Number(task.payload?.salience ?? 0),
          arousal: Number(task.payload?.arousal ?? 0),
          reward: Number(task.payload?.reward ?? 0),
          latency: Number(task.payload?.latency ?? 0),
        };
        const plan = this.model ? this.model.run(input) : { plan: 0.5 };
        output = {
          plan,
          route: plan.plan >= 0.5 ? NODE_ROLES.MOTOR : NODE_ROLES.DMN,
          explanation: 'executive planner generated route',
        };
      } else if (this.role === NODE_ROLES.DMN) {
        output = {
          reflection: `consolidated ${this.localEvents.length} local events`,
          route: NODE_ROLES.MEMORY,
          explanation: 'default mode consolidation and simulation',
        };
      } else if (this.role === NODE_ROLES.MEMORY) {
        output = {
          snapshotSize: this.localEvents.length,
          route: NODE_ROLES.DMN,
          explanation: 'memory snapshot compressed',
        };
      } else {
        output = {
          accepted: true,
          route: NODE_ROLES.COORDINATOR,
          explanation: 'generic execution node',
        };
      }

      return { event, output };
    } finally {
      this.inflight -= 1;
    }
  }
}

module.exports = { BrainNode, connectLineProtocol, write };
