const neo4j = require('neo4j-driver');

class Neo4jStore {
  constructor(config = {}) {
    this.enabled = Boolean(config.uri && config.username && config.password);
    this.config = config;
    this.driver = this.enabled
      ? neo4j.driver(config.uri, neo4j.auth.basic(config.username, config.password))
      : null;
  }

  async close() {
    if (this.driver) await this.driver.close();
  }

  async session(mode = 'write') {
    if (!this.driver) return null;
    return this.driver.session({
      defaultAccessMode: mode === 'read' ? neo4j.session.READ : neo4j.session.WRITE,
    });
  }

  async run(cypher, params = {}, mode = 'write') {
    if (!this.driver) return null;
    const session = await this.session(mode);
    try {
      return await session.run(cypher, params);
    } finally {
      await session.close();
    }
  }

  async ensureSchema() {
    if (!this.driver) return;
    const statements = [
      'CREATE CONSTRAINT dcos_node_id IF NOT EXISTS FOR (n:DCOSNode) REQUIRE n.id IS UNIQUE',
      'CREATE CONSTRAINT dcos_event_id IF NOT EXISTS FOR (e:DCOSEvent) REQUIRE e.id IS UNIQUE',
      'CREATE CONSTRAINT dcos_group_name IF NOT EXISTS FOR (g:DCOSGroup) REQUIRE g.name IS UNIQUE',
    ];
    for (const cypher of statements) await this.run(cypher);
  }

  async upsertNode(node) {
    return this.run(
      `MERGE (n:DCOSNode {id: $id})
       SET n.role = $role,
           n.host = $host,
           n.port = $port,
           n.status = $status,
           n.load = $load,
           n.lastSeen = datetime($lastSeen),
           n.capabilities = $capabilities
       RETURN n`,
      node
    );
  }

  async writeEvent(event) {
    return this.run(
      `MERGE (e:DCOSEvent {id: $id})
       SET e.type = $type,
           e.timestamp = datetime($timestamp),
           e.hash = $hash,
           e.prevHash = $prevHash,
           e.payload = $payload,
           e.origin = $origin,
           e.route = $route
       RETURN e`,
      {
        ...event,
        payload: JSON.stringify(event.payload),
      }
    );
  }

  async linkEventToNode(eventId, nodeId) {
    return this.run(
      `MATCH (e:DCOSEvent {id: $eventId}), (n:DCOSNode {id: $nodeId})
       MERGE (e)-[:EXECUTED_BY]->(n)`,
      { eventId, nodeId }
    );
  }
}

module.exports = { Neo4jStore };
