/* ═══════════════════════════════════════════════════════
   MAC MAESTRO — App Logic
   CORTEX Persist Control Panel
   ═══════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  // ── Sidebar Navigation ──────────────────────────
  const sidebarItems = document.querySelectorAll('.sidebar-item');
  const sections = document.querySelectorAll('.section');

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
  const search = document.getElementById('sidebarSearch');
  if (search) {
    search.addEventListener('input', () => {
      const q = search.value.toLowerCase();
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

  // ── Slider Value Sync ───────────────────────────
  document.querySelectorAll('.slider').forEach(slider => {
    const container = slider.closest('.slider-container');
    const valueEl = container?.querySelector('.slider-value');
    if (valueEl) {
      slider.addEventListener('input', () => {
        valueEl.textContent = `${slider.value}%`;
      });
    }
  });

  // ── Agent Row Selection ─────────────────────────
  const agentData = {
    tutor: {
      name: 'TUTOR',
      guard: 75,
      tier: 'TIER_1_LOCAL_SAFE',
      facts: '1,248',
      time: 'Today at 11:52 PM'
    },
    chema: {
      name: 'CHEMA',
      guard: 90,
      tier: 'TIER_2_NETWORK',
      facts: '847',
      time: 'Today at 11:48 PM'
    },
    legion: {
      name: 'LEGION',
      guard: 60,
      tier: 'TIER_3_EXTERNAL',
      facts: '2,105',
      time: 'Today at 10:30 PM'
    },
    sentinel: {
      name: 'SENTINEL',
      guard: 95,
      tier: 'TIER_2_NETWORK',
      facts: '573',
      time: 'Today at 11:51 PM'
    },
    apollo: {
      name: 'APOLLO',
      guard: 40,
      tier: 'TIER_1_LOCAL_SAFE',
      facts: '312',
      time: 'Yesterday at 8:12 PM'
    }
  };

  const agentRows = document.querySelectorAll('.agent-row');
  agentRows.forEach(row => {
    row.addEventListener('click', () => {
      agentRows.forEach(r => r.classList.remove('selected'));
      row.classList.add('selected');

      const id = row.dataset.agent;
      const data = agentData[id];
      if (!data) return;

      const detailName = document.getElementById('agentDetailName');
      const guardSlider = document.getElementById('guardSlider');
      const guardValue = document.getElementById('guardValue');
      const riskTier = document.getElementById('riskTier');

      if (detailName) detailName.textContent = `${data.name} — Agent Details`;
      if (guardSlider) {
        guardSlider.value = data.guard;
        if (guardValue) guardValue.textContent = `${data.guard}%`;
      }
      if (riskTier) riskTier.value = data.tier;

      // Update facts and time in detail panel
      const detailRows = document.querySelectorAll('#agentDetail .settings-row-value');
      if (detailRows.length >= 2) {
        detailRows[0].textContent = data.facts;
        detailRows[1].textContent = data.time;
      }
    });
  });

  // ── Ledger Ring Animation ───────────────────────
  const ringFill = document.getElementById('ringFill');
  if (ringFill) {
    const circumference = 2 * Math.PI * 60;
    ringFill.style.strokeDasharray = circumference;
    ringFill.style.strokeDashoffset = circumference;

    // Animate on section visibility
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          setTimeout(() => {
            ringFill.style.strokeDashoffset = '0';
          }, 200);
        }
      });
    });

    const ledgerSection = document.getElementById('section-ledger');
    if (ledgerSection) observer.observe(ledgerSection);

    // Also trigger when clicking sidebar
    sidebarItems.forEach(item => {
      if (item.dataset.section === 'ledger') {
        item.addEventListener('click', () => {
          ringFill.style.strokeDashoffset = circumference;
          setTimeout(() => {
            ringFill.style.strokeDashoffset = '0';
          }, 100);
        });
      }
    });
  }

  // ── Traffic Light Hover Effect ──────────────────
  const trafficLights = document.querySelectorAll('.traffic-light');
  const titlebar = document.querySelector('.titlebar');

  if (titlebar) {
    titlebar.addEventListener('mouseenter', () => {
      trafficLights.forEach(tl => tl.style.opacity = '1');
    });
  }

  // ── Keyboard Navigation ─────────────────────────
  document.addEventListener('keydown', (e) => {
    if (e.metaKey && e.key === 'f') {
      e.preventDefault();
      search?.focus();
    }

    // ⌘1-8 for sections
    if (e.metaKey && !e.shiftKey && !e.altKey) {
      const num = parseInt(e.key);
      if (num >= 1 && num <= 8) {
        e.preventDefault();
        const item = sidebarItems[num - 1];
        if (item) item.click();
      }
    }
  });
});

// ── Global Actions ────────────────────────────────
function verifyChain() {
  const btn = event.target;
  const originalText = btn.textContent;
  btn.textContent = 'Verifying...';
  btn.disabled = true;

  setTimeout(() => {
    btn.textContent = '✓ Chain Valid';
    btn.style.background = '#34C759';
    setTimeout(() => {
      btn.textContent = originalText;
      btn.style.background = '';
      btn.disabled = false;
    }, 2000);
  }, 1500);
}

function exportAudit() {
  const btn = event.target;
  const originalText = btn.textContent;
  btn.textContent = 'Exporting...';

  setTimeout(() => {
    btn.textContent = '✓ Report Exported';
    setTimeout(() => {
      btn.textContent = originalText;
    }, 2000);
  }, 1000);
}

document.addEventListener('DOMContentLoaded', () => {
  const syncBtn = document.getElementById('btnSyncConfluence');
  if (syncBtn) {
    syncBtn.addEventListener('click', () => {
      const originalText = syncBtn.textContent;
      syncBtn.textContent = 'Syncing...';
      syncBtn.disabled = true;

      // Simulate calling the cortex_confluence_sync tool
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
});

// ── Sheet Dialog Logic ────────────────────────────
let currentSheetAction = null;

function showDangerSheet(actionType) {
  const overlay = document.getElementById('macSheetOverlay');
  const title = document.getElementById('macSheetTitle');
  const text = document.getElementById('macSheetText');
  const btn = document.getElementById('macSheetConfirmBtn');
  
  currentSheetAction = actionType;

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
}

function closeSheet() {
  const overlay = document.getElementById('macSheetOverlay');
  overlay.classList.remove('active');
  currentSheetAction = null;
}

// Bind confirm button
document.addEventListener('DOMContentLoaded', () => {
  const confirmBtn = document.getElementById('macSheetConfirmBtn');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => {
      const originalText = confirmBtn.textContent;
      confirmBtn.textContent = 'Executing...';
      confirmBtn.disabled = true;

      setTimeout(() => {
        confirmBtn.textContent = '✓ Done';
        confirmBtn.style.background = 'var(--green)';
        setTimeout(() => {
          closeSheet();
          confirmBtn.textContent = originalText;
          confirmBtn.disabled = false;
        }, 1200);
      }, 1500);
    });
  }
});

// ── Enhanced Liveness (Autonomous Evolution) ──────
document.addEventListener('DOMContentLoaded', () => {
  // Simulate database fact ingestion
  const totalFactsEl = document.getElementById('totalFacts');
  if (totalFactsEl) {
    let currentFacts = parseInt(totalFactsEl.textContent.replace(/,/g, ''), 10);
    setInterval(() => {
      if (Math.random() > 0.7) {
        currentFacts += Math.floor(Math.random() * 3) + 1;
        totalFactsEl.textContent = new Intl.NumberFormat('en-US').format(currentFacts);
      }
    }, 2000);
  }

  // Uptime tick
  const uptimeEls = Array.from(document.querySelectorAll('.settings-row-value')).filter(el => el.textContent.includes('99.7%'));
  if (uptimeEls.length > 0) {
    let baseUptime = 99.700;
    setInterval(() => {
      baseUptime += 0.001;
      if (baseUptime > 99.999) baseUptime = 99.999;
      uptimeEls[0].textContent = baseUptime.toFixed(3) + '%';
    }, 5000);
  }
});
