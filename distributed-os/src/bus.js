const { EventEmitter } = require('node:events');
const { randomUUID } = require('node:crypto');
const { sha256, stableStringify } = require('../../brain-runtime/src/eventBus');

let nats = null;
try {
  nats = require('nats');
} catch {
  nats = null;
}

let sharedLocalBus = null;

function makeEnvelope({ nodeId, type, payload = {}, meta = {}, prevHash = 'GENESIS' }) {
  const timestamp = new Date().toISOString();
  const id = randomUUID();
  const body = { id, type, payload, meta, nodeId, timestamp, prevHash };
  const hash = sha256(`${prevHash}:${stableStringify(body)}`);
  return { ...body, hash };
}

class LocalSwarmBus {
  constructor() {
    this.emitter = new EventEmitter();
  }

  async connect() {
    return this;
  }

  async publish(subject, message) {
    queueMicrotask(() => this.emitter.emit(subject, message));
    return message;
  }

  async subscribe(subject, handler) {
    this.emitter.on(subject, handler);
    return {
      unsubscribe: () => this.emitter.off(subject, handler),
    };
  }

  async close() {
    this.emitter.removeAllListeners();
  }
}

class NatsSwarmBus {
  constructor(url) {
    if (!nats) {
      throw new Error('nats dependency is unavailable');
    }
    this.url = url;
    this.nc = null;
    this.codec = nats.StringCodec();
  }

  async connect() {
    this.nc = await nats.connect({ servers: this.url, name: 'cortex-persist-swarm' });
    return this;
  }

  async publish(subject, message) {
    const payload = this.codec.encode(JSON.stringify(message));
    this.nc.publish(subject, payload);
    return message;
  }

  async subscribe(subject, handler) {
    const sub = this.nc.subscribe(subject);
    (async () => {
      for await (const msg of sub) {
        try {
          handler(JSON.parse(this.codec.decode(msg.data)));
        } catch (err) {
          handler({ type: 'BUS_ERROR', error: err.message, raw: this.codec.decode(msg.data) });
        }
      }
    })().catch(() => {});
    return {
      unsubscribe: () => sub.unsubscribe(),
    };
  }

  async close() {
    if (this.nc) {
      await this.nc.close();
      this.nc = null;
    }
  }
}

async function createSwarmBus({ natsUrl } = {}) {
  if (natsUrl) {
    const transport = new NatsSwarmBus(natsUrl);
    return transport.connect();
  }
  if (!sharedLocalBus) {
    sharedLocalBus = new LocalSwarmBus();
    await sharedLocalBus.connect();
  }
  return sharedLocalBus;
}

module.exports = { createSwarmBus, makeEnvelope, LocalSwarmBus, NatsSwarmBus };
