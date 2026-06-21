const crypto = require('node:crypto');

const MESSAGE_TYPES = Object.freeze({
  REGISTER: 'REGISTER',
  HEARTBEAT: 'HEARTBEAT',
  SPIKE: 'SPIKE',
  ATTENTION_SHIFT: 'ATTENTION_SHIFT',
  STATE_CHANGE: 'STATE_CHANGE',
  REWARD_SIGNAL: 'REWARD_SIGNAL',
  ROUTE_DECISION: 'ROUTE_DECISION',
  SNAPSHOT: 'SNAPSHOT',
  TASK: 'TASK',
  RESULT: 'RESULT',
  SHUTDOWN: 'SHUTDOWN',
});

function stableStringify(value) {
  const seen = new WeakSet();
  return JSON.stringify(value, function (_key, val) {
    if (val && typeof val === 'object') {
      if (seen.has(val)) return '[Circular]';
      seen.add(val);
      if (!Array.isArray(val)) {
        return Object.keys(val).sort().reduce((acc, key) => {
          acc[key] = val[key];
          return acc;
        }, {});
      }
    }
    return val;
  });
}

function hashMessage(message) {
  return crypto.createHash('sha256').update(stableStringify(message)).digest('hex');
}

function createEnvelope({ type, source, target = null, payload = {}, meta = {}, prevHash = 'GENESIS' }) {
  const envelope = {
    id: crypto.randomUUID(),
    type,
    source,
    target,
    payload,
    meta,
    timestamp: new Date().toISOString(),
    prevHash,
  };
  envelope.hash = hashMessage(envelope);
  return envelope;
}

function validateEnvelope(envelope) {
  if (!envelope || typeof envelope !== 'object') return false;
  if (!envelope.type || !envelope.source || !envelope.timestamp || !envelope.hash) return false;
  return true;
}

module.exports = {
  MESSAGE_TYPES,
  createEnvelope,
  validateEnvelope,
  hashMessage,
  stableStringify,
};
