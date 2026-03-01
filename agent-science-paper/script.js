
/* ═══════════════════════════════════════════════
   La Ciencia del Agente — Interactive Engine
   ═══════════════════════════════════════════════ */

// ─── PARTICLES ───
(function initParticles() {
  const c = document.getElementById('particles');
  if (!c) return;
  const ctx = c.getContext('2d');
  let W, H, particles = [];
  const COUNT = 60;
  const COLORS = ['#CCFF00', '#6600FF', '#D4AF37', '#2E5090'];

  function resize() {
    W = c.width = window.innerWidth;
    H = c.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  for (let i = 0; i < COUNT; i++) {
    particles.push({
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.5 + 0.3,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      alpha: Math.random() * 0.4 + 0.1
    });
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0) p.x = W;
      if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H;
      if (p.y > H) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = p.alpha;
      ctx.fill();
    }
    // connections
    ctx.globalAlpha = 0.04;
    ctx.strokeStyle = '#CCFF00';
    ctx.lineWidth = 0.5;
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const d = dx * dx + dy * dy;
        if (d < 15000) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
        }
      }
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(draw);
  }
  draw();
})();

// ─── SCROLL PROGRESS ───
const progressBar = document.getElementById('progress');
function updateProgress() {
  const h = document.documentElement.scrollHeight - window.innerHeight;
  const pct = h > 0 ? (window.scrollY / h) * 100 : 0;
  progressBar.style.width = pct + '%';
}

// ─── SCROLL SPY ───
const sections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('.nav-links a');
function updateSpy() {
  const y = window.scrollY + 200;
  let current = '';
  sections.forEach(s => {
    if (s.offsetTop <= y) current = s.id;
  });
  navLinks.forEach(a => {
    a.classList.toggle('active', a.getAttribute('href') === '#' + current);
  });
}

// ─── HIDE NAV ON SCROLL DOWN ───
let lastY = 0;
const nav = document.getElementById('nav');
function updateNav() {
  const y = window.scrollY;
  if (y > lastY && y > 100) nav.classList.add('hidden');
  else nav.classList.remove('hidden');
  lastY = y;
}

// ─── INTERSECTION OBSERVER (reveal) ───
const observer = new IntersectionObserver(
  entries => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); }),
  { threshold: 0.08 }
);
sections.forEach(s => observer.observe(s));

// ─── TRIANGLE NODE CLICK ───
document.querySelectorAll('.tri-node').forEach(node => {
  node.addEventListener('click', () => {
    const target = node.dataset.section;
    const el = document.getElementById(target);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});

// ─── COMBINED SCROLL HANDLER (passive) ───
window.addEventListener('scroll', () => {
  updateProgress();
  updateSpy();
  updateNav();
}, { passive: true });

// ─── INITIAL CALLS ───
updateProgress();
updateSpy();
