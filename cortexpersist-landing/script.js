/* ============================================================
   CORTEX Persist — Landing Page Script
   Awwwards Sovereign Agent v3.6.0
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

  // ─── Pre-loader ───
  const loader = {
    overlay: document.querySelector('.loader-overlay'),
    bar: document.querySelector('.loader-bar'),
    counter: document.querySelector('.loader-counter'),

    run() {
      if (!this.overlay) return;
      const assets = [...document.images];
      const total = Math.max(assets.length, 1);
      let loaded = 0;

      const tick = () => {
        loaded++;
        const pct = Math.min(Math.round((loaded / total) * 100), 100);
        if (this.bar) this.bar.style.width = `${pct}%`;
        if (this.counter) this.counter.textContent = `${pct}%`;
      };

      const done = () => {
        if (this.bar) this.bar.style.width = '100%';
        if (this.counter) this.counter.textContent = '100%';

        setTimeout(() => {
          if (this.overlay) {
            this.overlay.style.transition = 'opacity 0.5s cubic-bezier(0.76, 0, 0.24, 1), transform 0.5s cubic-bezier(0.76, 0, 0.24, 1)';
            this.overlay.style.opacity = '0';
            this.overlay.style.transform = 'translateY(-20px)';
            setTimeout(() => this.overlay.remove(), 600);
          }
        }, 300);
      };

      if (assets.length === 0) {
        done();
        return;
      }

      Promise.all(assets.map(img => new Promise(resolve => {
        if (img.complete) { tick(); resolve(); }
        else {
          img.onload = img.onerror = () => { tick(); resolve(); };
        }
      }))).then(done);
    }
  };
  loader.run();

  // ─── Intersection Observer for .reveal ───
  if (!prefersReducedMotion) {
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          revealObserver.unobserve(entry.target);
        }
      });
    }, { root: null, rootMargin: '0px', threshold: 0.15 });

    document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));
  } else {
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
  }

  // ─── Pipeline Animation ───
  const pipelineTrack = document.getElementById('pipeline-track');
  if (pipelineTrack) {
    const nodes = pipelineTrack.querySelectorAll('.pipeline-node');
    const arrows = pipelineTrack.querySelectorAll('.pipeline-arrow');

    const pipelineObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animatePipeline(nodes, arrows);
          pipelineObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });

    pipelineObserver.observe(pipelineTrack);
  }

  function animatePipeline(nodes, arrows) {
    const baseDelay = prefersReducedMotion ? 0 : 200;
    nodes.forEach((node, i) => {
      setTimeout(() => {
        node.classList.add('active');
        if (arrows[i]) arrows[i].classList.add('active');
      }, i * baseDelay);
    });
  }

  // ─── Sovereign Cursor ───
  if (!isTouchDevice && !prefersReducedMotion) {
    const cursorDot = document.querySelector('.cursor-dot');
    const cursorRing = document.querySelector('.cursor-ring');

    if (cursorDot && cursorRing) {
      let mouseX = 0, mouseY = 0;
      let ringX = 0, ringY = 0;

      document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        cursorDot.style.left = `${mouseX}px`;
        cursorDot.style.top = `${mouseY}px`;
      });

      const followRing = () => {
        ringX += (mouseX - ringX) * 0.12;
        ringY += (mouseY - ringY) * 0.12;
        cursorRing.style.left = `${ringX}px`;
        cursorRing.style.top = `${ringY}px`;
        requestAnimationFrame(followRing);
      };
      followRing();

      // Magnetic effect on [data-magnetic]
      document.querySelectorAll('[data-magnetic]').forEach(el => {
        el.addEventListener('mouseenter', () => {
          cursorDot.classList.add('hovering');
          cursorRing.classList.add('hovering');
        });
        el.addEventListener('mouseleave', () => {
          cursorDot.classList.remove('hovering');
          cursorRing.classList.remove('hovering');
        });
      });
    }
  } else {
    // Remove cursor elements on touch
    document.querySelectorAll('.cursor-dot, .cursor-ring').forEach(el => el.remove());
  }

  // ─── Copy pip install ───
  const pipBtn = document.getElementById('pip-copy');
  if (pipBtn) {
    pipBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText('pip install cortex-persist');
        pipBtn.classList.add('copied');
        const original = pipBtn.querySelector('span:first-child').textContent;
        pipBtn.querySelector('span:first-child').textContent = 'Copied!';
        setTimeout(() => {
          pipBtn.classList.remove('copied');
          pipBtn.querySelector('span:first-child').textContent = original;
        }, 2000);
      } catch {
        // Fallback: select text
        const range = document.createRange();
        range.selectNodeContents(pipBtn.querySelector('span:first-child'));
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
      }
    });
  }

  // ─── Download Audit Artifact ───
  const downloadBtn = document.getElementById('download-artifact');
  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      const artifact = {
        entry_id: "ldg_2026-03-17_00042",
        fact_id: "f_a7c3e901",
        action: "CREATE",
        timestamp: "2026-03-17T09:15:22.841Z",
        hash: "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        prev_hash: "sha256:3c7e29a1d8b045f6a2e981c4d0762b38f4a9e8c7d6b5a4f3e2d1c0b9a8f7e6d5",
        tenant: "agent-alpha",
        guard_result: "PASS",
        payload_encrypted: true,
        schema_version: "v0.3",
        confidence: 0.92,
        source: "agent-runtime",
        metadata: {
          write_latency_ms: 3.7,
          guards_applied: ["admission", "contradiction", "dependency"],
          encryption: "AES-256-GCM"
        }
      };

      const blob = new Blob([JSON.stringify(artifact, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'cortex_audit_artifact.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  }
});
