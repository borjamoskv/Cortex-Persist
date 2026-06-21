const NODE_ROLES = Object.freeze({
  COORDINATOR: 'coordinator',
  DMN: 'dmn',
  CEN: 'cen',
  SN: 'sn',
  REGION: 'region',
});

const EVENT_TYPES = Object.freeze({
  SPIKE: 'SPIKE',
  STATE_CHANGE: 'STATE_CHANGE',
  ATTENTION_SHIFT: 'ATTENTION_SHIFT',
  REWARD_SIGNAL: 'REWARD_SIGNAL',
  ROUTE_DECISION: 'ROUTE_DECISION',
  HEARTBEAT: 'HEARTBEAT',
  REGISTER: 'REGISTER',
});

function routePolicy(event) {
  const salience = Number(event?.payload?.salience ?? 0);
  const reward = Number(event?.payload?.reward ?? 0);
  const arousal = Number(event?.payload?.arousal ?? 0);

  if (event.type === EVENT_TYPES.ATTENTION_SHIFT || salience >= 0.7 || arousal >= 0.8) {
    return [NODE_ROLES.SN, NODE_ROLES.CEN];
  }

  if (event.type === EVENT_TYPES.REWARD_SIGNAL || reward >= 0.6) {
    return [NODE_ROLES.CEN, NODE_ROLES.DMN];
  }

  if (event.type === EVENT_TYPES.SPIKE && salience < 0.4) {
    return [NODE_ROLES.DMN];
  }

  return [NODE_ROLES.CEN, NODE_ROLES.DMN];
}

module.exports = { NODE_ROLES, EVENT_TYPES, routePolicy };
