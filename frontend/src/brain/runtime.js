// Cortex-Persist Brain Runtime (C4-SIM)
// Node.js + Neo4j + Event Bus (deterministic cognitive kernel)

import neo4j from 'neo4j-driver'
import { EventEmitter } from 'events'
import crypto from 'crypto'

/**
 * Event Bus = Neural Spike Layer
 */
export class BrainEventBus extends EventEmitter {
  constructor() {
    super()
    this.log = [] // event-sourced memory
  }

  emitEvent(type, payload) {
    const event = {
      id: crypto.randomUUID(),
      type,
      timestamp: Date.now(),
      payload,
      hash: null
    }

    event.hash = this._hash(event)
    this.log.push(event)
    this.emit(type, event)

    return event
  }

  _hash(event) {
    return crypto
      .createHash('sha256')
      .update(JSON.stringify(event))
      .digest('hex')
  }

  replay(filterType = null) {
    return this.log.filter(e => !filterType || e.type === filterType)
  }
}

/**
 * Neo4j Brain Graph Connector
 */
export class BrainGraph {
  constructor(uri, user, password) {
    this.driver = neo4j.driver(uri, neo4j.auth.basic(user, password))
  }

  async run(query, params = {}) {
    const session = this.driver.session()
    try {
      return await session.run(query, params)
    } finally {
      await session.close()
    }
  }

  async createBrainRegion(region) {
    return this.run(
      `
      MERGE (r:BrainRegion {name: $name})
      SET r.layer = $layer,
          r.function = $function,
          r.latency_ms = $latency_ms,
          r.compute_model = $compute_model
      RETURN r
      `,
      region
    )
  }

  async connect(a, b, latency_ms = 10) {
    return this.run(
      `
      MATCH (r1:BrainRegion {name: $a})
      MATCH (r2:BrainRegion {name: $b})
      MERGE (r1)-[c:CONNECTS_TO]->(r2)
      SET c.latency_ms = $latency_ms
      RETURN c
      `,
      { a, b, latency_ms }
    )
  }
}

/**
 * Cortex Runtime = Executive Brain Kernel
 */
export class CortexRuntime {
  constructor(graph, bus) {
    this.graph = graph
    this.bus = bus
    this.state = {
      dmn: 'idle',
      cen: 'active',
      sn: 'monitoring'
    }

    this._bind()
  }

  _bind() {
    this.bus.on('SPIKE', this._onSpike.bind(this))
    this.bus.on('ATTENTION_SHIFT', this._onAttention.bind(this))
    this.bus.on('REWARD_SIGNAL', this._onReward.bind(this))
  }

  async _onSpike(event) {
    const { region, intensity } = event.payload

    await this.graph.run(
      `MATCH (r:BrainRegion {name:$region})
       SET r.last_spike = $t, r.intensity = $intensity`,
      { region, intensity, t: Date.now() }
    )
  }

  async _onAttention(event) {
    const { from, to } = event.payload

    this.state.dmn = from
    this.state.cen = to

    await this.graph.run(
      `MATCH (n:FunctionalNetwork)
       WHERE n.name IN [$from, $to]
       SET n.state = CASE n.name
         WHEN $from THEN 'deactivated'
         WHEN $to THEN 'active'
       END`,
      { from, to }
    )
  }

  async _onReward(event) {
    const { region, delta } = event.payload

    await this.graph.run(
      `MATCH (r:BrainRegion {name:$region})
       SET r.reward = coalesce(r.reward, 0) + $delta`,
      { region, delta }
    )
  }

  spike(region, intensity = 1.0) {
    return this.bus.emitEvent('SPIKE', { region, intensity })
  }

  shiftAttention(from, to, salience = 0.5) {
    return this.bus.emitEvent('ATTENTION_SHIFT', { from, to, salience })
  }

  reward(region, delta) {
    return this.bus.emitEvent('REWARD_SIGNAL', { region, delta })
  }
}

/**
 * Bootstrapping helper
 */
export function createCortexRuntime(config) {
  const bus = new BrainEventBus()
  const graph = new BrainGraph(
    config.NEO4J_URI,
    config.NEO4J_USER,
    config.NEO4J_PASSWORD
  )

  return new CortexRuntime(graph, bus)
}
