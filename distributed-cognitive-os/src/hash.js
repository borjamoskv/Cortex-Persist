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

function chainEvent(prevHash, event) {
  const basis = stableStringify({
    id: event.id,
    type: event.type,
    timestamp: event.timestamp,
    payload: event.payload,
    meta: event.meta,
  });
  return sha256(`${prevHash}:${basis}`);
}

module.exports = { stableStringify, sha256, chainEvent };
