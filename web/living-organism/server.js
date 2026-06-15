import express from 'express';
import fs from 'fs';
import path from 'path';

const app = express();
app.use(express.json());

const DATA_FILE = path.resolve('./web/living-organism/events.log.jsonl');

function readEvents() {
  if (!fs.existsSync(DATA_FILE)) return [];
  const raw = fs.readFileSync(DATA_FILE, 'utf-8').trim();
  if (!raw) return [];
  return raw.split('\n').map(l => JSON.parse(l));
}

function writeEvent(evt) {
  fs.appendFileSync(DATA_FILE, JSON.stringify(evt) + '\n');
}

function reduceState(events) {
  const nodes = new Map();

  for (const e of events) {
    if (e.type === 'INIT') {
      e.payload.nodes.forEach(n => nodes.set(n.id, n));
    }

    if (e.type === 'MUTATE') {
      const n = nodes.get(e.payload.id);
      if (n) nodes.set(e.payload.id, { ...n, ...e.payload.patch });
    }

    if (e.type === 'SPAWN') {
      nodes.set(e.payload.node.id, e.payload.node);
    }

    if (e.type === 'KILL') {
      nodes.delete(e.payload.id);
    }
  }

  return { nodes: Array.from(nodes.values()), tick: events.length };
}

app.get('/api/state', (req, res) => {
  const events = readEvents();
  res.json(reduceState(events));
});

app.post('/api/event', (req, res) => {
  const evt = {
    type: req.body.type,
    payload: req.body.payload,
    ts: Date.now()
  };
  writeEvent(evt);
  res.json({ ok: true });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`living organism API running on ${PORT}`);
});