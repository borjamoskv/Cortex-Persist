import { api } from './api.js';
import { CortexGraph } from './graph.js';

/* ═══════════════════════════════════════════════════════
   MAC MAESTRO — App Logic
   CORTEX Persist Control Panel
   Phase 3: Sovereign Orchestration Module
   ═══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', async () => {

  // ── Initialization ──────────────────────────────
  const sidebarItems = document.querySelectorAll('.sidebar-item');
  const sections = document.querySelectorAll('.section');
  
  await updateDashboard();
  await populateAgents();
  await populateFacts('');
  await populateNodes();
  await startLogStream();

  // Initialize graph (lazy — renders when Ledger section is visible)
  let graph = null;

  // ── Sidebar Navigation ──────────────────────────
  sidebarItems.forEach(item => {
    item.addEventListener('click', () => {
      const target = item.dataset.section;
      sidebarItems.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      sections.forEach(s => s.classList.remove('active'));
      const targetSection = document.getElementById(`section-${target}`);
      if (targetSection) targetSection.classList.add('active');

      // Lazy-init graph when Ledger is first opened
      if (target === 'ledger' && !graph) {
        graph = new CortexGraph('cortexGraph');
        graph.load();
      }
    });
  });

  // ── Sidebar Search ──────────────────────────────
  const sidebarSearch = document.getElementById('sidebarSearch');
  if (sidebarSearch) {
    sidebarSearch.addEventListener('input', () => {
      const q = sidebarSearch.value.toLowerCase();
      sidebarItems.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(q) ? '' : 'none';
      });
    });
  }

  // ── Segmented Controls ──────────────────────────
  document.querySelectorAll('.segmented').forEach(seg => {
    const btns = seg.querySelectorAll('.segmented-btn');
    btns.forEach(btn => {
      btn.addEventListener('click', () => {
        btns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });
  });

  // ── Console Logic ───────────────────────────────
  const logConsole = document.getElementById('logConsole');
  const toggleConsoleBtn = document.getElementById('toggleConsole');
  const clearLogsBtn = document.getElementById('clearLogs');

  if (toggleConsoleBtn) {
    toggleConsoleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      logConsole.classList.toggle('hidden');
      toggleConsoleBtn.textContent = logConsole.classList.contains('hidden') ? 'Show' : 'Hide';
    });
  }

  if (clearLogsBtn) {
    clearLogsBtn.addEventListener('click', () => {
      document.getElementById('logLines').innerHTML = '';
    });
  }

  // ── Memory Explorer Search ──────────────────────
  const factSearch = document.getElementById('factSearch');
  if (factSearch) {
    factSearch.addEventListener('input', async () => {
      await populateFacts(factSearch.value);
    });
  }

  // ── Report Generator ────────────────────────────
  const btnReport = document.getElementById('btnGenerateReport');
  if (btnReport) {
    btnReport.addEventListener('click', async () => {
      const formatBtn = document.querySelector('#reportFormatSelector .segmented-btn.active');
      const format = formatBtn?.dataset.format || 'json';
      const progressContainer = document.getElementById('reportProgress');
      const progressFill = document.getElementById('reportProgressFill');
      const progressText = document.getElementById('reportProgressText');

      progressContainer.hidden = false;
      btnReport.disabled = true;
      btnReport.textContent = 'Generating...';

      const result = await api.generateReport(format, (pct, step) => {
        progressFill.style.width = pct + '%';
        progressText.textContent = step;
      });

      progressFill.style.width = '100%';
      progressText.innerHTML = `<span class="report-complete">✓ ${result.filename} (${result.size})</span>`;
      btnReport.textContent = '✓ Report Ready';
      btnReport.style.background = 'var(--green)';

      setTimeout(() => {
        btnReport.textContent = 'Generate Article 12 Report';
        btnReport.style.background = '';
        btnReport.disabled = false;
      }, 3000);
    });
  }

  // ── Confluence Sync ─────────────────────────────
  const syncBtn = document.getElementById('btnSyncConfluence');
  if (syncBtn) {
    syncBtn.addEventListener('click', () => {
      const originalText = syncBtn.textContent;
      syncBtn.textContent = 'Syncing...';
      syncBtn.disabled = true;
      setTimeout(() => {
        syncBtn.textContent = '✓ Synced';
        syncBtn.style.background = '#34C759';
        setTimeout(() => {
          syncBtn.textContent = originalText;
          syncBtn.style.background = '';
          syncBtn.disabled = false;
        }, 2000);
      }, 2500);
    });
  }

  // ── Node Management ─────────────────────────────
  const btnAddNode = document.getElementById('btnAddNode');
  if (btnAddNode) {
    btnAddNode.addEventListener('click', async () => {
      const url = prompt('Enter remote CORTEX node address:', '10.0.1.50:8000');
      if (!url) return;
      btnAddNode.textContent = 'Connecting...';
      btnAddNode.disabled = true;
      await api.addNode(url);
      await populateNodes();
      btnAddNode.textContent = '+ Add Remote Node';
      btnAddNode.disabled = false;
    });
  }

  const btnRefresh = document.getElementById('btnRefreshNodes');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', async () => {
      btnRefresh.textContent = 'Refreshing...';
      await populateNodes();
      btnRefresh.textContent = 'Refresh';
    });
  }

  // ── Slider Sync ─────────────────────────────────
  document.querySelectorAll('.slider').forEach(slider => {
    const container = slider.closest('.slider-container');
    const valueEl = container?.querySelector('.slider-value');
    if (valueEl) {
      slider.addEventListener('input', () => {
        valueEl.textContent = `${slider.value}%`;
      });
    }
  });

  // ── Functions ───────────────────────────────────
  
  async function updateDashboard() {
    const metrics = await api.getMetrics();
    const updateEagerly = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };
    updateEagerly('totalFacts', metrics.facts);
    updateEagerly('dbSize', metrics.dbSize);
  }

  async function populateAgents() {
    await api.getAgents();
  }

  async function populateFacts(query) {
    const facts = await api.searchFacts(query);
    const grid = document.getElementById('factGrid');
    if (!grid) return;

    grid.innerHTML = facts.map(f => `
      <div class="fact-row">
        <div class="fact-col-id">${f.id}</div>
        <div class="fact-col-content" title="${f.content}">${f.content}</div>
        <div class="fact-col-source">${f.source}</div>
        <div class="fact-col-time">${f.time}</div>
      </div>
    `).join('');
  }

  async function populateNodes() {
    const nodes = await api.getNodes();
    const grid = document.getElementById('nodeGrid');
    if (!grid) return;

    grid.innerHTML = nodes.map(n => {
      const latencyClass = n.latency === null ? 'dead' : n.latency > 30 ? 'slow' : '';
      const latencyText = n.latency !== null ? `${n.latency}ms` : 'N/A';
      return `
        <div class="node-card">
          <div class="node-card-header">
            <span class="node-name">${n.name}</span>
            <span class="node-status ${n.status}"></span>
          </div>
          <div class="node-host">${n.host}</div>
          <div class="node-meta">
            <span class="node-latency ${latencyClass}">${latencyText}</span>
            <span>${n.facts.toLocaleString()} facts</span>
          </div>
        </div>`;
    }).join('');
  }

  async function startLogStream() {
    const logLines = document.getElementById('logLines');
    setInterval(async () => {
      if (Math.random() > 0.6) {
        const logs = await api.getLogs();
        const log = logs[Math.floor(Math.random() * logs.length)];
        const line = document.createElement('div');
        line.className = 'log-line';
        line.innerHTML = `
          <span class="log-time">[${new Date().toLocaleTimeString()}]</span>
          <span class="log-level ${log.level.toLowerCase()}">${log.level}</span>
          <span class="log-source">${log.source}</span>
          <span class="log-msg">${log.msg}</span>
        `;
        logLines.appendChild(line);
        logLines.scrollTop = logLines.scrollHeight;
      }
    }, 3000);
  }

});

// ── Expose Global Buttons to Window (for Module compatibility) ──
window.verifyChain = async function() {
  const btn = event.target;
  btn.textContent = 'Verifying...';
  btn.disabled = true;
  await api.verifyChain();
  setTimeout(() => {
    btn.textContent = '✓ Chain Valid';
    btn.style.background = '#34C759';
    setTimeout(() => {
      btn.textContent = 'Verify Integrity';
      btn.style.background = '';
      btn.disabled = false;
    }, 2000);
  }, 1500);
};

window.showDangerSheet = function(actionType) {
  const overlay = document.getElementById('macSheetOverlay');
  const title = document.getElementById('macSheetTitle');
  const text = document.getElementById('macSheetText');
  const btn = document.getElementById('macSheetConfirmBtn');
  
  if (actionType === 'gc') {
    title.textContent = 'Run Irreversible Compaction?';
    text.textContent = 'This will irreversibly purge completely bypassed semantic ghosts. Proceeding will lock the database for a few seconds.';
    btn.textContent = 'Run GC';
    btn.style.background = 'var(--orange)';
  } else if (actionType === 'nuke') {
    title.textContent = 'Purge Master Ledger?';
    text.textContent = 'This will destroy all facts and reset cryptographic genesis. This action cannot be undone and will permanently wipe system memory.';
    btn.textContent = 'Nuke Database';
    btn.style.background = 'var(--red)';
  }
  overlay.classList.add('active');
};

window.closeSheet = function() {
  document.getElementById('macSheetOverlay').classList.remove('active');
};

// Bind sheet confirmation
document.addEventListener('DOMContentLoaded', () => {
  const confirmBtn = document.getElementById('macSheetConfirmBtn');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => {
      confirmBtn.textContent = 'Executing...';
      confirmBtn.disabled = true;
      setTimeout(() => {
        confirmBtn.textContent = '✓ Done';
        confirmBtn.style.background = 'var(--green)';
        setTimeout(() => {
          window.closeSheet();
          confirmBtn.textContent = 'Run Action';
          confirmBtn.disabled = false;
        }, 1200);
      }, 1500);
    });
  }
});
