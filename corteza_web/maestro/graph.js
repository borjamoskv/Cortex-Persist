import { api } from './api.js';

/**
 * MAC MAESTRO — Force-Directed Graph Renderer
 * Zero-dependency canvas visualization for Agent-Fact dependencies
 */

export class CortexGraph {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.nodes = [];
    this.edges = [];
    this.dragging = null;
    this.mouse = { x: 0, y: 0 };
    this.dpr = window.devicePixelRatio || 1;
    this.animId = null;

    this.resize();
    window.addEventListener('resize', () => this.resize());
    this.canvas.addEventListener('mousedown', e => this.onMouseDown(e));
    this.canvas.addEventListener('mousemove', e => this.onMouseMove(e));
    this.canvas.addEventListener('mouseup', () => this.onMouseUp());
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width * this.dpr;
    this.canvas.height = 350 * this.dpr;
    this.canvas.style.width = rect.width + 'px';
    this.canvas.style.height = '350px';
    this.ctx.scale(this.dpr, this.dpr);
    this.width = rect.width;
    this.height = 350;
  }

  async load() {
    const data = await api.getGraph();
    if (!data) return;
    this.nodes = data.nodes.map(n => ({
      ...n,
      vx: 0, vy: 0,
      radius: n.type === 'agent' ? 28 : 16
    }));
    this.edges = data.edges;
    this.animate();
  }

  animate() {
    this.simulate();
    this.draw();
    this.animId = requestAnimationFrame(() => this.animate());
  }

  simulate() {
    const k = 0.005;  // Spring constant
    const repulsion = 8000;
    const damping = 0.85;
    const center = { x: this.width / 2, y: this.height / 2 };

    // Repulsion between all nodes
    for (let i = 0; i < this.nodes.length; i++) {
      for (let j = i + 1; j < this.nodes.length; j++) {
        const a = this.nodes[i], b = this.nodes[j];
        let dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = repulsion / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx -= fx; a.vy -= fy;
        b.vx += fx; b.vy += fy;
      }
    }

    // Spring attraction along edges
    for (const edge of this.edges) {
      const a = this.nodes.find(n => n.id === edge.from);
      const b = this.nodes.find(n => n.id === edge.to);
      if (!a || !b) continue;
      const dx = b.x - a.x, dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = (dist - 120) * k;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx += fx; a.vy += fy;
      b.vx -= fx; b.vy -= fy;
    }

    // Center gravity
    for (const n of this.nodes) {
      if (n === this.dragging) continue;
      n.vx += (center.x - n.x) * 0.001;
      n.vy += (center.y - n.y) * 0.001;
      n.vx *= damping;
      n.vy *= damping;
      n.x += n.vx;
      n.y += n.vy;
      // Bounds
      n.x = Math.max(n.radius, Math.min(this.width - n.radius, n.x));
      n.y = Math.max(n.radius, Math.min(this.height - n.radius, n.y));
    }
  }

  draw() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);

    // Background grid
    ctx.strokeStyle = 'rgba(255,255,255,0.03)';
    ctx.lineWidth = 1;
    for (let x = 0; x < this.width; x += 40) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, this.height); ctx.stroke();
    }
    for (let y = 0; y < this.height; y += 40) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(this.width, y); ctx.stroke();
    }

    // Edges
    for (const edge of this.edges) {
      const a = this.nodes.find(n => n.id === edge.from);
      const b = this.nodes.find(n => n.id === edge.to);
      if (!a || !b) continue;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = 'rgba(255,255,255,0.12)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Nodes
    for (const n of this.nodes) {
      // Glow
      const gradient = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.radius * 2);
      gradient.addColorStop(0, n.color + '40');
      gradient.addColorStop(1, 'transparent');
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius * 2, 0, Math.PI * 2);
      ctx.fill();

      // Body
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
      ctx.fillStyle = n.color;
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.2)';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Label
      ctx.fillStyle = '#fff';
      ctx.font = n.type === 'agent' ? 'bold 10px -apple-system, sans-serif' : '9px -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const label = n.label.length > 10 ? n.label.substr(0, 9) + '…' : n.label;
      ctx.fillText(label, n.x, n.y);
    }
  }

  onMouseDown(e) {
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    for (const n of this.nodes) {
      const dx = mx - n.x, dy = my - n.y;
      if (dx * dx + dy * dy < n.radius * n.radius) {
        this.dragging = n;
        this.canvas.style.cursor = 'grabbing';
        break;
      }
    }
  }

  onMouseMove(e) {
    if (!this.dragging) return;
    const rect = this.canvas.getBoundingClientRect();
    this.dragging.x = e.clientX - rect.left;
    this.dragging.y = e.clientY - rect.top;
    this.dragging.vx = 0;
    this.dragging.vy = 0;
  }

  onMouseUp() {
    this.dragging = null;
    this.canvas.style.cursor = 'grab';
  }

  destroy() {
    if (this.animId) cancelAnimationFrame(this.animId);
  }
}
