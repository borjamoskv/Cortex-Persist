// NEXUS — UI Components (Vanilla JS)

export function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export function createTrustRing(posteriorMean, tier, size = 56) {
  const r = (size - 4) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - posteriorMean);
  const colors = {
    unverified: '#555570', bronze: '#CD7F32',
    silver: '#C0C0C0', gold: '#FFD700', sovereign: '#2B3BE5'
  };
  const color = colors[tier] || colors.unverified;

  return `<svg class="trust-ring" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="3"/>
    <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="3"
      stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
      stroke-linecap="round" transform="rotate(-90 ${size/2} ${size/2})"
      style="transition: stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1)"/>
  </svg>`;
}

export function createAgentCard(agent) {
  const initial = escapeHtml(agent.name ? agent.name.charAt(0) : '');
  const trust = agent.trust || {};
  const tier = trust.tier || 'unverified';
  const mean = trust.posterior_mean || 0;
  const caps = (agent.capabilities || []).slice(0, 3);
  const status = agent.status || 'offline';

  return `<div class="agent-card" data-agent-id="${escapeHtml(agent.id)}" onclick="window.app.showAgent('${escapeHtml(agent.id)}')">
    <div class="agent-card-header">
      <div class="agent-avatar">
        ${createTrustRing(mean, tier)}
        <div class="agent-avatar-inner">${initial}</div>
      </div>
      <div>
        <div class="agent-name">${escapeHtml(agent.name)}</div>
        <div class="agent-owner">${escapeHtml(agent.owner || 'Independent')}</div>
      </div>
      <div style="margin-left:auto; display:flex; align-items:center; gap:8px;">
        <div class="status-dot ${status}"></div>
        <span class="trust-badge ${tier}">${tier.toUpperCase()}</span>
      </div>
    </div>
    <div class="agent-desc">${escapeHtml(agent.description || '')}</div>
    <div class="agent-footer">
      <div class="cap-badges">
        ${caps.map(c => `<span class="cap-badge">${escapeHtml(c)}</span>`).join('')}
      </div>
      <span style="font-family:var(--mono);font-size:11px;color:var(--text-muted);">μ=${mean.toFixed(3)}</span>
    </div>
  </div>`;
}

export function createActivityItem(event, index) {
  const iconMap = {
    registration: { cls: 'registration', icon: '⬡' },
    trust_verify: { cls: 'verify', icon: '✓' },
    trust_task_complete: { cls: 'task', icon: '◆' },
    trust_vouch: { cls: 'vouch', icon: '★' },
    task_created: { cls: 'task', icon: '📋' },
  };
  const ic = iconMap[event.event_type] || { cls: '', icon: '•' };
  const time = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : '';

  return `<div class="activity-item" style="animation-delay:${index * 0.05}s">
    <div class="activity-icon ${ic.cls}">${ic.icon}</div>
    <div class="activity-text">${escapeHtml(event.description || event.event_type)}</div>
    <div class="activity-time">${time}</div>
  </div>`;
}

export function createStatsBar(stats) {
  return `<div class="stats-bar">
    <div class="stat-card">
      <div class="stat-label">Total Agents</div>
      <div class="stat-value electric">${stats.total_agents || 0}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Verified</div>
      <div class="stat-value success">${stats.verified_agents || 0}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Online Now</div>
      <div class="stat-value" style="color:var(--text)">${stats.online_agents || 0}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Tasks Completed</div>
      <div class="stat-value gold">${stats.tasks_completed || 0}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Avg Trust</div>
      <div class="stat-value electric">${(stats.avg_trust_score || 0).toFixed(3)}</div>
    </div>
  </div>`;
}

export function createAgentDetail(agent) {
  const trust = agent.trust || {};
  const tier = trust.tier || 'unverified';
  const mean = trust.posterior_mean || 0;
  const tierColor = {
    unverified: 'var(--tier-unverified)', bronze: 'var(--tier-bronze)',
    silver: 'var(--tier-silver)', gold: 'var(--tier-gold)', sovereign: 'var(--tier-sovereign)'
  }[tier] || 'var(--text-muted)';

  return `<div class="agent-detail">
    <button class="back-btn" onclick="window.app.navigate('directory')">← Back to Directory</button>
    <div class="detail-header">
      <div class="detail-avatar">
        ${createTrustRing(mean, tier, 92)}
        <div class="agent-avatar-inner" style="font-size:32px">${escapeHtml(agent.name ? agent.name.charAt(0) : '')}</div>
      </div>
      <div style="flex:1">
        <div style="display:flex;align-items:center;gap:12px">
          <div class="detail-name">${escapeHtml(agent.name)}</div>
          <div class="status-dot ${agent.status}"></div>
          <span class="trust-badge ${tier}">${tier.toUpperCase()}</span>
        </div>
        <div class="detail-desc">${escapeHtml(agent.description || '')}</div>
        <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">
          ${(agent.capabilities||[]).map(c => `<span class="cap-badge">${escapeHtml(c)}</span>`).join('')}
        </div>
      </div>
    </div>

    <div class="detail-grid">
      <div class="detail-card">
        <div class="detail-card-title">Trust Score</div>
        <div style="display:flex;align-items:baseline;gap:8px">
          <span style="font-family:var(--mono);font-size:32px;font-weight:700;color:${tierColor}">${mean.toFixed(4)}</span>
          <span style="font-size:12px;color:var(--text-muted)">posterior mean</span>
        </div>
        <div class="trust-meter">
          <div class="trust-meter-fill" style="width:${mean*100}%;background:${tierColor}"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:8px;font-family:var(--mono);font-size:11px;color:var(--text-muted)">
          <span>α=${(trust.alpha||0).toFixed(1)}</span>
          <span>β=${(trust.beta||0).toFixed(1)}</span>
          <span>signals=${trust.total_signals||0}</span>
        </div>
      </div>

      <div class="detail-card">
        <div class="detail-card-title">Performance</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px">
          <div>
            <div style="font-size:11px;color:var(--text-muted)">Tasks Completed</div>
            <div style="font-family:var(--mono);font-size:24px;font-weight:700;color:var(--success)">${agent.tasks_completed||0}</div>
          </div>
          <div>
            <div style="font-size:11px;color:var(--text-muted)">Tasks Failed</div>
            <div style="font-family:var(--mono);font-size:24px;font-weight:700;color:var(--danger)">${agent.tasks_failed||0}</div>
          </div>
        </div>
      </div>

      <div class="detail-card">
        <div class="detail-card-title">Identity</div>
        <div style="font-family:var(--mono);font-size:11px;color:var(--text-dim);word-break:break-all;margin-top:4px">
          ${escapeHtml(agent.public_key || 'No key assigned')}
        </div>
        <div style="margin-top:8px;font-size:12px;color:var(--text-muted)">
          Owner: <strong style="color:var(--text)">${escapeHtml(agent.owner||'—')}</strong>
        </div>
      </div>

      <div class="detail-card">
        <div class="detail-card-title">Metadata</div>
        <div style="font-size:12px;color:var(--text-dim);display:flex;flex-direction:column;gap:4px;margin-top:4px">
          <span>Registered: ${agent.registered_at ? new Date(agent.registered_at).toLocaleDateString() : '—'}</span>
          <span>Last Seen: ${agent.last_seen ? new Date(agent.last_seen).toLocaleString() : '—'}</span>
          <span>Agent ID: <code style="font-family:var(--mono);color:var(--electric)">${escapeHtml(agent.id)}</code></span>
        </div>
      </div>
    </div>
  </div>`;
}

export function createTaskCard(task, agents) {
  const caps = (task.required_capabilities || []).slice(0, 3);
  const capBadges = caps.map(c => `<span class="cap-badge">${escapeHtml(c)}</span>`).join('');

  let actionHtml = '';
  if (task.status === 'open') {
    const eligibleAgents = agents.filter(a => a.status === 'online');
    actionHtml = `
      <div class="task-action-row" style="margin-top: 12px; display: flex; gap: 8px;">
        <select class="search-input" id="assignee-select-${escapeHtml(task.id)}" style="padding: 6px 12px; font-size: 12px; height: 32px; width: auto; flex: 1;">
          <option value="">-- Choose Agent --</option>
          ${eligibleAgents.map(a => `<option value="${escapeHtml(a.id)}">${escapeHtml(a.name)}</option>`).join('')}
        </select>
        <button class="back-btn" onclick="window.app.assignTask('${escapeHtml(task.id)}')" style="margin: 0; padding: 6px 12px; height: 32px; background: var(--electric); color: white; border: none;">Assign</button>
      </div>
    `;
  } else if (task.status === 'assigned') {
    const assignee = agents.find(a => a.id === task.assignee_id);
    actionHtml = `
      <div style="margin-top: 12px; font-size: 12px; color: var(--text-dim);">
        Assigned to: <strong style="color: var(--text)">${assignee ? escapeHtml(assignee.name) : escapeHtml(task.assignee_id)}</strong>
      </div>
      <div class="task-action-row" style="margin-top: 8px; display: flex; gap: 8px;">
        <button class="back-btn" onclick="window.app.completeTask('${escapeHtml(task.id)}')" style="margin: 0; padding: 6px 12px; height: 32px; background: var(--success); color: black; border: none; font-weight: bold;">Complete</button>
        <button class="back-btn" onclick="window.app.failTask('${escapeHtml(task.id)}')" style="margin: 0; padding: 6px 12px; height: 32px; background: var(--danger); color: white; border: none;">Fail</button>
      </div>
    `;
  } else {
    const assignee = agents.find(a => a.id === task.assignee_id);
    actionHtml = `
      <div style="margin-top: 12px; font-size: 12px; color: var(--text-dim);">
        Assignee: <strong style="color: var(--text)">${assignee ? escapeHtml(assignee.name) : escapeHtml(task.assignee_id || 'None')}</strong>
        ${task.completed_at ? `<br/>Completed: ${new Date(task.completed_at).toLocaleString()}` : ''}
      </div>
    `;
  }

  return `
    <div class="agent-card" style="cursor: default;">
      <div class="agent-card-header" style="align-items: flex-start;">
        <div>
          <div class="agent-name" style="font-size: 16px;">${escapeHtml(task.title)}</div>
          <div class="agent-owner" style="font-family: var(--mono); font-size: 10px; margin-top: 2px;">ID: ${escapeHtml(task.id)}</div>
        </div>
        <div style="margin-left: auto; display: flex; align-items: center; gap: 8px;">
          <span class="trust-badge" style="background: var(--surface-2); color: var(--text-dim); text-transform: uppercase;">${escapeHtml(task.status)}</span>
        </div>
      </div>
      <div class="agent-desc" style="-webkit-line-clamp: 4; display: block; overflow: visible; height: auto;">${escapeHtml(task.description || 'No description provided')}</div>
      <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border); padding-top: 10px; margin-top: 10px;">
        <div class="cap-badges">${capBadges}</div>
        <div style="font-family: var(--mono); font-weight: bold; color: var(--tier-gold); font-size: 14px;">${task.reward.toFixed(1)} EXA</div>
      </div>
      ${actionHtml}
    </div>
  `;
}

export function createTasksView(tasks, agents) {
  const capabilities = [
    'code', 'security', 'intel', 'data', 'creative',
    'marketing', 'osint', 'infra', 'finance', 'research', 'legal', 'design'
  ];

  const taskCards = tasks.length
    ? tasks.map(t => createTaskCard(t, agents)).join('')
    : '<div class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-text">No tasks available</div></div>';

  return `
    <div class="tasks-layout" style="display: grid; grid-template-columns: 1fr 350px; gap: 24px;">
      <div>
        <div class="section-title">Active Tasks</div>
        <div class="agent-grid" style="grid-template-columns: 1fr;">
          ${taskCards}
        </div>
      </div>

      <div>
        <div class="section-title">Create Task</div>
        <div class="detail-card" style="position: sticky; top: 100px;">
          <form id="create-task-form" onsubmit="event.preventDefault(); window.app.submitTask();">
            <div style="margin-bottom: 12px;">
              <label style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); display: block; margin-bottom: 4px;">Task Title</label>
              <input class="search-input" id="task-title" required minlength="3" placeholder="e.g. Audit Smart Contracts" style="padding: 10px 14px;">
            </div>

            <div style="margin-bottom: 12px;">
              <label style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); display: block; margin-bottom: 4px;">Description</label>
              <textarea class="search-input" id="task-desc" placeholder="Provide instructions for the agent..." style="padding: 10px 14px; min-height: 100px; font-family: var(--font); resize: vertical;"></textarea>
            </div>

            <div style="margin-bottom: 12px;">
              <label style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); display: block; margin-bottom: 4px;">Reward (EXA)</label>
              <input type="number" class="search-input" id="task-reward" value="100" min="0" step="0.1" style="padding: 10px 14px;">
            </div>

            <div style="margin-bottom: 16px;">
              <label style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); display: block; margin-bottom: 6px;">Required Capabilities</label>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; max-height: 120px; overflow-y: auto; padding: 8px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-sm);">
                ${capabilities.map(c => `
                  <label style="display: flex; align-items: center; gap: 6px; font-size: 12px; cursor: pointer; color: var(--text-dim);">
                    <input type="checkbox" name="task-caps" value="${escapeHtml(c)}">
                    <span>${escapeHtml(c)}</span>
                  </label>
                `).join('')}
              </div>
            </div>

            <button type="submit" class="back-btn" style="width: 100%; margin: 0; padding: 12px; background: var(--electric); color: white; border: none; font-weight: bold; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">Publish Task</button>
          </form>
        </div>
      </div>
    </div>
  `;
}
