const { Neo4jStore } = require('../../brain-runtime/src/neo4j');

class DistributedGraphStore {
  constructor(neo4jConfig) {
    this.base = new Neo4jStore(neo4jConfig);
  }

  async ensureSchema() {
    await this.base.ensureSchema();
    await this.base.withSession(async (session) => {
      await session.run('CREATE CONSTRAINT agent_node_id IF NOT EXISTS FOR (n:Agent) REQUIRE n.nodeId IS UNIQUE');
      await session.run('CREATE CONSTRAINT swarm_task_id IF NOT EXISTS FOR (n:SwarmTask) REQUIRE n.taskId IS UNIQUE');
    });
  }

  async upsertAgent(agent) {
    const cypher = `
      MERGE (n:Agent {nodeId: $nodeId})
      SET n.role = $role,
          n.status = $status,
          n.load = $load,
          n.lastSeenAt = datetime($lastSeenAt),
          n.version = $version
      RETURN n
    `;
    return this.base.withSession((session) => session.run(cypher, agent));
  }

  async heartbeat({ nodeId, role, load, queueDepth, version, status = 'alive' }) {
    return this.upsertAgent({
      nodeId,
      role,
      status,
      load,
      version,
      lastSeenAt: new Date().toISOString(),
    });
  }

  async attachAgentToRegion(nodeId, regionName) {
    const cypher = `
      MATCH (a:Agent {nodeId: $nodeId}), (r:BrainRegion {name: $regionName})
      MERGE (a)-[rel:HOSTS]->(r)
      RETURN rel
    `;
    return this.base.withSession((session) => session.run(cypher, { nodeId, regionName }));
  }

  async assignTask({ taskId, type, targetRole, targetNodeId, payload }) {
    const cypher = `
      MERGE (t:SwarmTask {taskId: $taskId})
      SET t.type = $type,
          t.targetRole = $targetRole,
          t.targetNodeId = $targetNodeId,
          t.payload = $payload,
          t.status = 'assigned',
          t.updatedAt = datetime()
      RETURN t
    `;
    return this.base.withSession((session) => session.run(cypher, {
      taskId,
      type,
      targetRole,
      targetNodeId,
      payload: JSON.stringify(payload ?? {}),
    }));
  }

  async recordCompletion({ taskId, nodeId, output }) {
    const cypher = `
      MATCH (t:SwarmTask {taskId: $taskId})
      SET t.status = 'completed',
          t.nodeId = $nodeId,
          t.output = $output,
          t.completedAt = datetime(),
          t.updatedAt = datetime()
      RETURN t
    `;
    return this.base.withSession((session) => session.run(cypher, {
      taskId,
      nodeId,
      output: JSON.stringify(output ?? {}),
    }));
  }

  async recordEnvelope(envelope) {
    return this.base.writeEvent(envelope);
  }

  async close() {
    return this.base.close();
  }
}

module.exports = { DistributedGraphStore };
