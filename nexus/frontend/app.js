import { createAgentCard, createActivityItem, createStatsBar, createAgentDetail, createTasksView, escapeHtml } from './components.js';

const API = '/api';

class NexusApp {
  constructor() {
    this.agents = [];
    this.stats = {};
    this.activity = [];
    this.tasks = [];
    this.currentView = 'directory';
    this.searchQuery = '';
    this.filterCap = null;
    this.init();
  }

  async init() {
    await this.fetchData();
    this.render();
    this.bindEvents();
    // Refresh activity every 15s
    setInterval(() => this.refreshActivity(), 15000);
  }

  async fetchData() {
    try {
      const [agents, stats, activity, tasks] = await Promise.all([
        fetch(`${API}/agents`).then(r => r.json()),
        fetch(`${API}/stats`).then(r => r.json()),
        fetch(`${API}/activity`).then(r => r.json()),
        fetch(`${API}/tasks`).then(r => r.json()),
      ]);
      this.agents = agents;
      this.stats = stats;
      this.activity = activity;
      this.tasks = tasks;
    } catch (e) {
      console.warn('API unavailable, using empty state:', e.message);
      this.agents = [];
      this.stats = { total_agents: 0, verified_agents: 0, online_agents: 0, tasks_completed: 0, avg_trust_score: 0 };
      this.activity = [];
      this.tasks = [];
    }
  }

  async refreshActivity() {
    try {
      this.activity = await fetch(`${API}/activity`).then(r => r.json());
      if (this.currentView === 'activity') this.renderActivity();
    } catch {}
  }

  // ── Routing ──────────────────────────────────────────────

  navigate(view, param = null) {
    this.currentView = view;
    this.currentParam = param;
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.view === view));
    this.renderView();
  }

  async showAgent(agentId) {
    this.currentView = 'detail';
    this.currentParam = agentId;
    this.renderView();
  }

  // ── Rendering ────────────────────────────────────────────

  render() {
    const statsEl = document.getElementById('stats-container');
    if (statsEl) statsEl.innerHTML = createStatsBar(this.stats);
    this.renderView();
  }

  renderView() {
    const main = document.getElementById('main-content');
    if (!main) return;

    // Fade transition
    main.style.opacity = '0';
    main.style.transform = 'translateY(8px)';

    setTimeout(() => {
      switch (this.currentView) {
        case 'directory': this.renderDirectory(main); break;
        case 'tasks': this.renderTasks(main); break;
        case 'activity': this.renderActivityView(main); break;
        case 'detail': this.renderDetail(main); break;
        default: this.renderDirectory(main);
      }
      requestAnimationFrame(() => {
        main.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        main.style.opacity = '1';
        main.style.transform = 'translateY(0)';
      });
    }, 150);
  }

  renderDirectory(container) {
    const caps = [...new Set(this.agents.flatMap(a => a.capabilities || []))].sort();
    let filtered = this.agents;

    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      filtered = filtered.filter(a =>
        a.name.toLowerCase().includes(q) ||
        (a.description || '').toLowerCase().includes(q)
      );
    }
    if (this.filterCap) {
      filtered = filtered.filter(a => (a.capabilities || []).includes(this.filterCap));
    }

    container.innerHTML = `
      <div class="section-title">Agent Directory</div>
      <div class="search-container">
        <span class="search-icon">⌕</span>
        <input class="search-input" id="search" placeholder="Search agents by name or capability...">
      </div>
      <div class="filters">
        <span class="filter-pill ${!this.filterCap ? 'active' : ''}" data-cap="">All</span>
        ${caps.map(c => `<span class="filter-pill ${this.filterCap === c ? 'active' : ''}" data-cap="${escapeHtml(c)}">${escapeHtml(c)}</span>`).join('')}
      </div>
      <div class="agent-grid">
        ${filtered.length ? filtered.map(a => createAgentCard(a)).join('') : '<div class="empty-state"><div class="empty-state-icon">⬡</div><div class="empty-state-text">No agents found</div></div>'}
      </div>
    `;

    // Bind search
    const searchInput = document.getElementById('search');
    if (searchInput) {
      searchInput.value = this.searchQuery || '';
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value;
        this.renderDirectory(container);
        const input = document.getElementById('search');
        if (input) {
          input.focus();
          const len = input.value.length;
          input.setSelectionRange(len, len);
        }
      });
    }

    // Bind filters
    container.querySelectorAll('.filter-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        this.filterCap = pill.dataset.cap || null;
        this.renderDirectory(container);
      });
    });
  }

  renderActivityView(container) {
    container.innerHTML = `
      <div class="section-title">Activity Feed</div>
      <div class="activity-list">
        ${this.activity.length
          ? this.activity.map((e, i) => createActivityItem(e, i)).join('')
          : '<div class="empty-state"><div class="empty-state-icon">⚡</div><div class="empty-state-text">No activity yet</div></div>'
        }
      </div>
    `;
  }

  renderActivity() {
    if (this.currentView !== 'activity') return;
    const container = document.getElementById('main-content');
    if (container) this.renderActivityView(container);
  }

  renderDetail(container) {
    const agent = this.agents.find(a => a.id === this.currentParam);
    if (!agent) {
      container.innerHTML = '<div class="empty-state"><div class="empty-state-text">Agent not found</div></div>';
      return;
    }
    container.innerHTML = createAgentDetail(agent);
  }

  // ── Events ───────────────────────────────────────────────

  renderTasks(container) {
    container.innerHTML = createTasksView(this.tasks, this.agents);
  }

  async submitTask() {
    const title = document.getElementById('task-title').value.trim();
    const description = document.getElementById('task-desc').value.trim();
    const reward = parseFloat(document.getElementById('task-reward').value) || 0.0;
    
    const checkboxes = document.querySelectorAll('input[name="task-caps"]:checked');
    const required_capabilities = Array.from(checkboxes).map(cb => cb.value);

    try {
      const res = await fetch(`${API}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          description,
          required_capabilities,
          reward,
          delegator_id: 'system'
        })
      });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || 'Failed to create task');
      }
      await this.fetchData();
      this.render();
    } catch (e) {
      alert(`Error creating task: ${e.message}`);
    }
  }

  async assignTask(taskId) {
    const select = document.getElementById(`assignee-select-${taskId}`);
    const assigneeId = select ? select.value : '';
    if (!assigneeId) {
      alert('Please select an agent to assign the task to.');
      return;
    }

    try {
      const res = await fetch(`${API}/tasks/${taskId}/assign/${assigneeId}`, {
        method: 'POST'
      });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || 'Assignment failed');
      }
      await this.fetchData();
      this.render();
    } catch (e) {
      alert(`Error assigning task: ${e.message}`);
    }
  }

  async completeTask(taskId) {
    try {
      const res = await fetch(`${API}/tasks/${taskId}/complete`, {
        method: 'POST'
      });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || 'Complete operation failed');
      }
      await this.fetchData();
      this.render();
    } catch (e) {
      alert(`Error completing task: ${e.message}`);
    }
  }

  async failTask(taskId) {
    const reason = prompt('Enter failure reason (optional):') || 'Failed';
    try {
      const res = await fetch(`${API}/tasks/${taskId}/fail?reason=${encodeURIComponent(reason)}`, {
        method: 'POST'
      });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || 'Fail operation failed');
      }
      await this.fetchData();
      this.render();
    } catch (e) {
      alert(`Error failing task: ${e.message}`);
    }
  }

  bindEvents() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
      btn.addEventListener('click', () => this.navigate(btn.dataset.view));
    });
  }
}

// Boot
window.app = new NexusApp();
