import { api } from './api.js';

/* ═══════════════════════════════════════════════════════
   MAC MAESTRO — App Logic
   CORTEX Persist Control Panel
   Synaptic Connectivity Module
   ═══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', async () => {

  // ── Initialization ──────────────────────────────
  const sidebarItems = document.querySelectorAll('.sidebar-item');
  const sections = document.querySelectorAll('.section');
  
  // Initial population
  await updateDashboard();
  await populateAgents();
  await populateFacts('');
  await startLogStream();

  // ── Sidebar Navigation ──────────────────────────
  sidebarItems.forEach(item => {
    item.addEventListener('click', () => {
      const target = item.dataset.section;
      sidebarItems.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      sections.forEach(s => s.classList.remove('active'));
      const targetSection = document.getElementById(`section-${target}`);
      if (targetSection) targetSection.classList.add('active');
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
    const agents = await api.getAgents();
    // Implementation for dynamic injection if needed, 
    // but current HTML has static ones for Tier demo.
    // For now, let's keep the row selection logic.
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
