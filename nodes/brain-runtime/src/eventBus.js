const { EventEmitter } = require('node:events');
const crypto = require('node:crypto');

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

class EventBus extends EventEmitter {
  constructor() {
    super();
    this.log = [];
    this.lastHash = 'GENESIS';
  }

  publish(type, payload = {}, meta = {}) {
    const event = {
      id: crypto.randomUUID(),
      type,
      timestamp: new Date().toISOString(),
      payload,
      meta,
      prevHash: this.lastHash,
    };

    event.hash = sha256(`${event.prevHash}:${stableStringify({ type, payload, meta, timestamp: event.timestamp, id: event.id })}`);
    this.lastHash = event.hash;
    this.log.push(event);
    this.emit(type, event);
    this.emit('*', event);
    return event;
  }

  replay(handler) {
    for (const event of this.log) handler(event);
  }

  snapshot() {
    return this.log.map((e) => ({ ...e }));
  }
}

module.exports = { EventBus, stableStringify, sha256 };
