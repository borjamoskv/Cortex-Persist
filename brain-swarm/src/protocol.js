const crypto = require('node:crypto');

const MESSAGE_TYPES = Object.freeze({
  REGISTER: 'REGISTER',
  REGISTERED: 'REGISTERED',
  HEARTBEAT: 'HEARTBEAT',
  HEARTBEAT_ACK: 'HEARTBEAT_ACK',
  TASK: 'TASK',
  TASK_RESULT: 'TASK_RESULT',
  EVENT: 'EVENT',
  ROUTE: 'ROUTE',
  SYNC: 'SYNC',
  SNAPSHOT: 'SNAPSHOT',
  SHUTDOWN: 'SHUTDOWN',
  ERROR: 'ERROR',
});

const NODE_ROLES = Object.freeze({
  COORDINATOR: 'COORDINATOR',
  DMN: 'DMN',
  CEN: 'CEN',
  SN: 'SN',
  MEMORY: 'MEMORY',
  MOTOR: 'MOTOR',
  SENSOR: 'SENSOR',
});

function makeId() {
  return crypto.randomUUID();
}

function createMessage(type, payload = {}, meta = {}) {
  return {
    id: makeId(),
    type,
    timestamp: new Date().toISOString(),
    payload,
    meta,
  };
}

function encode(message) {
  return `${JSON.stringify(message)}\n`;
}

function safeParse(line) {
  if (!line || !line.trim()) return null;
  try {
    return JSON.parse(line);
  } catch {
    return null;
  }
}

module.exports = {
  MESSAGE_TYPES,
  NODE_ROLES,
  makeId,
  createMessage,
  encode,
  safeParse,
};
