/**
 * MAC MAESTRO API Client
 * Synaptic Connectivity Layer for CORTEX Persist
 * Phase 3: Sovereign Orchestration
 */

class MaestroAPI {
  constructor() {
    this.baseUrl = 'http://localhost:8000';
    this.isMock = true;
    this.mockData = {
      metrics: {
        facts: 4721,
        height: 47,
        dbSize: '1.34 GB',
        uptime: '14d 2h 31m'
      },
      agents: [
        { id: 'tutor', name: 'TUTOR', role: 'Knowledge Base Management', status: 'active', avatar: '🎓', color: 'bg-blue' },
        { id: 'chema', name: 'CHEMA', role: 'Anomaly Detection + Immunization', status: 'active', avatar: '🔬', color: 'bg-indigo' },
        { id: 'legion', name: 'LEGION', role: 'Swarm Orchestration (Top Level)', status: 'idle', avatar: '⚔', color: 'bg-green' },
        { id: 'sentinel', name: 'SENTINEL', role: 'Security Ops / Penetration', status: 'active', avatar: '👁', color: 'bg-orange' }
      ],
      recentLogs: [
        { time: '00:24:12', level: 'INFO', source: 'ENGINE', msg: 'Ledger integrity verified successfully.' },
        { time: '00:25:01', level: 'DEBUG', source: 'TUTOR', msg: 'Ingesting 14 new facts from documentation update.' },
        { time: '00:26:45', level: 'INFO', source: 'CHEMA', msg: 'Scanning memory for semantic ghosts...' },
        { time: '00:27:10', level: 'INFO', source: 'LEGION', msg: 'Swarm heartbeat — 4 agents responsive.' },
        { time: '00:28:02', level: 'DEBUG', source: 'SENTINEL', msg: 'Port scan complete. No anomalies.' },
        { time: '00:29:15', level: 'INFO', source: 'ENGINE', msg: 'Compaction cycle #47 completed. 12 ghosts purged.' }
      ],
      nodes: [
        { id: 'local', host: 'localhost:8000', name: 'Primary (Local)', status: 'online', latency: 2, facts: 4721 },
        { id: 'staging', host: '10.0.1.42:8000', name: 'Staging Node', status: 'online', latency: 14, facts: 3102 },
        { id: 'eu-west', host: 'eu-west.cortex.internal:8000', name: 'EU-West (Compliance)', status: 'online', latency: 48, facts: 1847 },
        { id: 'backup', host: '10.0.1.99:8000', name: 'Backup Node', status: 'offline', latency: null, facts: 4200 }
      ],
      graph: {
        nodes: [
          { id: 'tutor', type: 'agent', label: 'TUTOR', color: '#0A84FF', x: 300, y: 200 },
          { id: 'chema', type: 'agent', label: 'CHEMA', color: '#5E5CE6', x: 500, y: 150 },
          { id: 'legion', type: 'agent', label: 'LEGION', color: '#30D158', x: 400, y: 350 },
          { id: 'sentinel', type: 'agent', label: 'SENTINEL', color: '#FF9F0A', x: 200, y: 350 },
          { id: 'f1', type: 'fact', label: 'EU AI Act Art.12', color: '#8E8E93', x: 350, y: 100 },
          { id: 'f2', type: 'fact', label: 'Pricing Model', color: '#8E8E93', x: 150, y: 200 },
          { id: 'f3', type: 'fact', label: 'Immunity Rules', color: '#8E8E93', x: 550, y: 300 },
          { id: 'f4', type: 'fact', label: 'Ledger Genesis', color: '#8E8E93', x: 300, y: 400 },
          { id: 'f5', type: 'fact', label: 'Guard Policies', color: '#8E8E93', x: 450, y: 250 }
        ],
        edges: [
          { from: 'tutor', to: 'f1' }, { from: 'tutor', to: 'f2' },
          { from: 'chema', to: 'f3' }, { from: 'chema', to: 'f5' },
          { from: 'legion', to: 'f4' }, { from: 'legion', to: 'f1' },
          { from: 'sentinel', to: 'f5' }, { from: 'sentinel', to: 'f3' },
          { from: 'tutor', to: 'f5' }
        ]
      }
    };
  }

  async getMetrics() {
    if (this.isMock) return delay(this.mockData.metrics, 300);
  }

  async getAgents() {
    if (this.isMock) return delay(this.mockData.agents, 200);
  }

  async getLogs() {
    if (this.isMock) return delay(this.mockData.recentLogs, 100);
  }

  async verifyChain() {
    if (this.isMock) {
      return { status: 'started', jobId: 'v_' + Math.random().toString(36).substr(2, 9) };
    }
  }

  async searchFacts(query) {
    if (this.isMock) {
      const results = [
        { id: 'f102', content: 'CORTEX Persist pricing starts at $0 for local agents.', source: 'website', time: '2026-03-18' },
        { id: 'f442', content: 'EU AI Act Article 12 requires automatic record-keeping.', source: 'legal_docs', time: '2026-03-17' },
        { id: 'f981', content: 'The immunity system uses semantic gap analysis.', source: 'chema_core', time: '2026-03-18' },
        { id: 'f1024', content: 'Guard policies enforce admission control on all write paths.', source: 'architecture', time: '2026-03-18' },
        { id: 'f1103', content: 'Ledger genesis block uses SHA-256 with zero-knowledge proof.', source: 'cryptography', time: '2026-03-16' }
      ];
      return results.filter(f => f.content.toLowerCase().includes(query.toLowerCase()));
    }
  }

  async getNodes() {
    if (this.isMock) return delay(this.mockData.nodes, 250);
  }

  async addNode(url) {
    if (this.isMock) {
      const node = { id: 'new_' + Date.now(), host: url, name: 'New Node', status: 'connecting', latency: null, facts: 0 };
      this.mockData.nodes.push(node);
      return delay(node, 500);
    }
  }

  async getGraph() {
    if (this.isMock) return delay(this.mockData.graph, 300);
  }

  async generateReport(format, onProgress) {
    if (this.isMock) {
      const steps = ['Collecting facts...', 'Auditing ledger...', 'Validating guards...', 'Compiling report...', 'Finalizing...'];
      for (let i = 0; i < steps.length; i++) {
        await delay(null, 600);
        if (onProgress) onProgress(((i + 1) / steps.length) * 100, steps[i]);
      }
      return { status: 'complete', format, filename: `cortex_art12_report.${format}`, size: '2.4 MB' };
    }
  }
}

function delay(data, ms) {
  return new Promise(resolve => setTimeout(() => resolve(data), ms));
}

export const api = new MaestroAPI();

