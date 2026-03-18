/**
 * MAC MAESTRO API Client
 * Synaptic Connectivity Layer for CORTEX Persist
 */

class MaestroAPI {
  constructor() {
    this.baseUrl = 'http://localhost:8000'; // Default CORTEX FastAPI port
    this.isMock = true; // Default to mock until backend is verified
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
        { time: '00:26:45', level: 'INFO', source: 'CHEMA', msg: 'Scanning memory for semantic ghosts...' }
      ]
    };
  }

  async getMetrics() {
    if (this.isMock) {
      return new Promise(resolve => setTimeout(() => resolve(this.mockData.metrics), 300));
    }
    // Real call: return fetch(`${this.baseUrl}/metrics`).then(r => r.json());
  }

  async getAgents() {
    if (this.isMock) {
      return new Promise(resolve => setTimeout(() => resolve(this.mockData.agents), 200));
    }
  }

  async getLogs() {
    if (this.isMock) {
      return new Promise(resolve => setTimeout(() => resolve(this.mockData.recentLogs), 100));
    }
  }

  async verifyChain() {
    if (this.isMock) {
      // Simulate progress
      return { status: 'started', jobId: 'v_' + Math.random().toString(36).substr(2, 9) };
    }
  }

  async searchFacts(query) {
    if (this.isMock) {
      // Simulated search results
      const results = [
        { id: 'f102', content: 'CORTEX Persist pricing starts at $0 for local agents.', source: 'website', time: '2026-03-18' },
        { id: 'f442', content: 'EU AI Act Article 12 requires automatic record-keeping.', source: 'legal_docs', time: '2026-03-17' },
        { id: 'f981', content: 'The immunity system uses semantic gap analysis.', source: 'chema_core', time: '2026-03-18' }
      ];
      return results.filter(f => f.content.toLowerCase().includes(query.toLowerCase()));
    }
  }
}

export const api = new MaestroAPI();
