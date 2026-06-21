const neo4j = require('neo4j-driver');

class SwarmNeo4jStore {
  constructor({ uri, username, password }) {
    this.enabled = Boolean(uri && username && password);
    this.driver = this.enabled ? neo4j.driver(uri, neo4j.auth.basic(username, password)) : null;
  }

  async close() {
    if (this.driver) await this.driver.close();
  }

  async withSession(work) {
    if (!this.driver) return null;
    const session = this.driver.session({ defaultAccessMode: neo4j.session.WRITE });
    try {
      return await work(session);
    } finally {
      await session.close();
    }
  }

  async ensureSchema() {
    if (!this.driver) return;
    const cypher = [
      'CREATE CONSTRAINT swarm_node_id IF NOT EXISTS FOR (n:SwarmNode) REQUIRE n.id IS UNIQUE',
      'CREATE CONSTRAINT swarm_event_id IF NOT EXISTS FOR (e:SwarmEvent) REQUIRE e.id IS UNIQUE',
      'CREATE CONSTRAINT swarm_snapshot_id IF NOT EXISTS FOR (s:SwarmSnapshot) REQUIRE s.id IS UNIQUE',
    ];
    await this.withSession(async (session) => {
      for (const stmt of cypher) await session.run(stmt);
    });
  }

  async upsertNode(node) {
    if (!this.driver) return null;
    return this.withSession((session) => session.run(
      `MERGE (n:SwarmNode {id: $id})
       SET n.role = $role,
           n.port = $port,
           n.status = $status,
           n.load = $load,
           n.updated_at = datetime($updated_at)
       RETURN n`,
      node
    ));
  }

  async writeEvent(event) {
    if (!this.driver) return null;
    return this.withSession((session) => session.run(
      `MERGE (e:SwarmEvent {id: $id})
       SET e.type = $type,
           e.source = $source,
           e.target = $target,
           e.payload = $payload,
           e.hash = $hash,
           e.prevHash = $prevHash,
           e.timestamp = datetime($timestamp)
       RETURN e`,
      {
        ...event,
        payload: JSON.stringify(event.payload),
      }
    ));
  }

  async writeSnapshot(snapshot) {
    if (!this.driver) return null;
    return this.withSession((session) => session.run(
      `MERGE (s:SwarmSnapshot {id: $id})
       SET s.payload = $payload,
           s.hash = $hash,
           s.timestamp = datetime($timestamp)
       RETURN s`,
      {
        ...snapshot,
        payload: JSON.stringify(snapshot.payload),
      }
    ));
  }
}

module.exports = { SwarmNeo4jStore };
