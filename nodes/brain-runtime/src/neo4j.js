const neo4j = require('neo4j-driver');

class Neo4jStore {
  constructor({ uri, username, password }) {
    if (!uri || !username || !password) {
      throw new Error('Neo4j config incomplete: uri, username, password are required');
    }
    this.driver = neo4j.driver(uri, neo4j.auth.basic(username, password));
  }

  async close() {
    await this.driver.close();
  }

  async withSession(work, mode = 'write') {
    const session = this.driver.session({ defaultAccessMode: mode === 'read' ? neo4j.session.READ : neo4j.session.WRITE });
    try {
      return await work(session);
    } finally {
      await session.close();
    }
  }

  async ensureSchema() {
    const statements = [
      'CREATE CONSTRAINT brain_region_name IF NOT EXISTS FOR (n:BrainRegion) REQUIRE n.name IS UNIQUE',
      'CREATE CONSTRAINT functional_network_name IF NOT EXISTS FOR (n:FunctionalNetwork) REQUIRE n.name IS UNIQUE',
      'CREATE CONSTRAINT neuromodulator_name IF NOT EXISTS FOR (n:Neuromodulator) REQUIRE n.name IS UNIQUE',
      'CREATE CONSTRAINT event_id IF NOT EXISTS FOR (n:Event) REQUIRE n.id IS UNIQUE',
    ];

    await this.withSession(async (session) => {
      for (const cypher of statements) {
        await session.run(cypher);
      }
    });
  }

  async upsertBrainRegion(region) {
    const cypher = `
      MERGE (n:BrainRegion {name: $name})
      SET n.layer = $layer,
          n.function = $function,
          n.latency_ms = $latency_ms,
          n.compute_model = $compute_model
      RETURN n
    `;
    return this.withSession((session) => session.run(cypher, region));
  }

  async upsertFunctionalNetwork(network) {
    const cypher = `
      MERGE (n:FunctionalNetwork {name: $name})
      SET n.frequency_hz = $frequency_hz,
          n.state = $state
      RETURN n
    `;
    return this.withSession((session) => session.run(cypher, network));
  }

  async upsertNeuromodulator(mod) {
    const cypher = `
      MERGE (n:Neuromodulator {name: $name})
      SET n.source = $source,
          n.effect = $effect
      RETURN n
    `;
    return this.withSession((session) => session.run(cypher, mod));
  }

  async connectRegions(from, to, props = {}) {
    const cypher = `
      MATCH (a:BrainRegion {name: $from}), (b:BrainRegion {name: $to})
      MERGE (a)-[r:CONNECTS_TO]->(b)
      SET r += $props
      RETURN r
    `;
    return this.withSession((session) => session.run(cypher, { from, to, props }));
  }

  async attachToNetwork(region, network) {
    const cypher = `
      MATCH (a:BrainRegion {name: $region}), (b:FunctionalNetwork {name: $network})
      MERGE (a)-[r:PART_OF]->(b)
      RETURN r
    `;
    return this.withSession((session) => session.run(cypher, { region, network }));
  }

  async modulate(region, modulator, props = {}) {
    const cypher = `
      MATCH (a:Neuromodulator {name: $modulator}), (b:BrainRegion {name: $region})
      MERGE (a)-[r:MODULATES]->(b)
      SET r += $props
      RETURN r
    `;
    return this.withSession((session) => session.run(cypher, { region, modulator, props }));
  }

  async writeEvent(event) {
    const cypher = `
      MERGE (e:Event {id: $id})
      SET e.type = $type,
          e.timestamp = datetime($timestamp),
          e.payload = $payload,
          e.hash = $hash,
          e.prevHash = $prevHash
      RETURN e
    `;
    return this.withSession((session) => session.run(cypher, {
      id: event.id,
      type: event.type,
      timestamp: event.timestamp,
      payload: JSON.stringify(event.payload),
      hash: event.hash,
      prevHash: event.prevHash,
    }));
  }
}

module.exports = { Neo4jStore };
