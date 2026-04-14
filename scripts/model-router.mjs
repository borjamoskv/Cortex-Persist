#!/usr/bin/env node

const fs = await import('node:fs');

const MODEL_MATRIX = [
  {
    id: 'gpt-5.4',
    name: 'gpt-5.4',
    focus: 'arquitectura, producto y decisiones complejas',
    signals: [
      'arquitectura',
      'arquitectura/',
      'roadmap',
      'diseño',
      'estrategia',
      'diseño de producto',
      'tradeoff',
      'trade-offs',
      'análisis',
      'auditor',
      'auditoría',
      'revisión de alto nivel',
      'propuesta',
      'decisión',
      'planteamiento',
      'sistema',
      'informe',
      'análisis técnico',
      'benchmark',
      'comparativa',
    ],
    base: 1.4,
    weight: 2.6,
  },
  {
    id: 'gpt-5.4-mini',
    name: 'gpt-5.4-Mini',
    focus: 'consultas técnicas rápidas con razonamiento sólido',
    signals: [
      'explicación',
      'explica',
      'duda',
      'cómo',
      'cómo',
      'qué modelo',
      'selección',
      'recomendación',
      'ayuda',
      'asesoría',
      'comparar modelos',
      'cómo hacerlo',
      'decidir',
      'trade-off',
      'opción',
    ],
    base: 1.0,
    weight: 1.9,
  },
  {
    id: 'gpt-5.3-codex',
    name: 'gpt-5.3-codex',
    focus: 'código real: refactors, bugs, integración y despliegue',
    signals: [
      'código',
      'frontend',
      'backend',
      'bug',
      'arreglar',
      'fix',
      'deploy',
      'despliegue',
      'build',
      'refactor',
      'función',
      'api',
      'integración',
      'pipeline',
      'test',
      'ci',
      'github',
      'pr',
      'merge',
      'error',
      'stack trace',
      'revisión',
      'endpoint',
    ],
    base: 2.0,
    weight: 3.0,
  },
  {
    id: 'gpt-5.3-codex-spark',
    name: 'gpt-5.3-codex-spark',
    focus: 'micro-ajustes rápidos en UI, texto o configuración pequeña',
    signals: [
      'micro',
      'ajuste',
      'copia',
      'copy',
      'colores',
      'css',
      'texto',
      'typo',
      'spacing',
      'ui',
      'retoque',
      'pequeño',
      'rápido',
      'rápida',
      'literal',
      'renombrar',
      'formateo',
      'pulir',
      'limpiar',
      'recortar',
    ],
    base: 1.3,
    weight: 2.8,
  },
  {
    id: 'gpt-5.2',
    name: 'gpt-5.2',
    focus: 'coordinación larga o tareas de sesión extensa',
    signals: [
      'sprint',
      'roadmap',
      'plan',
      'seguimiento',
      'coordinar',
      'coordinación',
      'revisión de proyecto',
      'gestión',
      'timeline',
      'próximos pasos',
      'recap',
      'síntesis',
      'estado',
      'sesión',
      'largo',
      'holística',
      'estrategia anual',
    ],
    base: 1.1,
    weight: 1.7,
  },
];

const FLAGS = {
  json: false,
  guide: false,
  agentId: 1,
};

const args = process.argv.slice(2);
if (args.includes('--help') || args.includes('-h')) {
  printHelp();
  process.exit(0);
}

FLAGS.json = args.includes('--json');
FLAGS.guide = args.includes('--guide');
FLAGS.agentId = readAgentId(args);

if (FLAGS.guide) {
  printGuide(FLAGS.json);
  process.exit(0);
}

const text = (args
  .filter((arg) => arg !== '--json')
  .filter((arg) => arg !== '--guide')
  .filter((arg) => arg !== '--agent')
  .filter((arg) => !arg.startsWith('--agent='))
  .join(' ')
  .trim()
  || fs.readFileSync(0, 'utf8').toString().trim());

if (!text) {
  printHelp();
  process.exit(1);
}

const result = selectModel(text, FLAGS.agentId);

if (FLAGS.json) {
  process.stdout.write(JSON.stringify(result, null, 2));
  process.stdout.write('\n');
  process.exit(0);
}

process.stdout.write(`${result.recommended.id} (${Math.round(result.recommended.confidence)}%)`);
process.stdout.write(` — ${result.recommended.reason}\n`);
process.stdout.write(`Alternativas:\n`);
for (const alt of result.alternatives) {
  process.stdout.write(`- ${alt.id} (${Math.round(alt.confidence)}%) | ${alt.reason}\n`);
}

function selectModel(rawText, agentId) {
  const text = normaliza(rawText);
  const tokens = splitTokens(text);
  const matches = MODEL_MATRIX.map((model) => ({
    ...model,
    score: model.base,
    hitCount: 0,
    matched: [],
  }));

  for (const entry of matches) {
    for (const signal of entry.signals) {
      const hasHit = new RegExp(`\\b${escapeRegex(signal)}\\b`, 'i').test(rawText)
        || signal.split(' ').every((part) => text.includes(part));
      if (hasHit) {
        entry.score += entry.weight;
        entry.hitCount += 1;
        entry.matched.push(signal);
      }
    }
  }

  // Heurística para mensajes muy cortos: preferir velocidad si son cambios puntuales.
  if (tokens.length < 7) {
    const spark = matches.find((m) => m.id === 'gpt-5.3-codex-spark');
    if (spark) {
      spark.score += 1.6;
    }
  }

  // Refuerza codex-spark en tareas de "parche", "cambio", "ajuste".
  const deltaTokens = ['parche', 'patch', 'ajusta', 'toca', 'tweak', 'retoque', 'pulir'];
  if (deltaTokens.some((tok) => tokens.includes(tok))) {
    const spark = matches.find((m) => m.id === 'gpt-5.3-codex-spark');
    if (spark) {
      spark.score += 1.2;
    }
  }

  const sorted = matches
    .map((entry) => {
      const boost = getAgentBoost(entry.id, agentId);
      const maxHit = MODEL_MATRIX.length ? 5 : 1;
      const hitBoost = (entry.hitCount / maxHit) * 18;
      const lengthBoost = Math.min(14, tokens.length);
      const confidence = Math.max(8, Math.min(99, Math.round(entry.score + hitBoost + lengthBoost + boost)));
      return {
        id: entry.id,
        name: entry.name,
        reason: `Perfil: ${entry.focus}. Señales: ${entry.hitCount ? entry.matched.slice(0, 4).join(', ') : 'ninguna fuerte'}.`,
        confidence,
      };
    })
    .sort((a, b) => b.confidence - a.confidence);

  return {
    inputPreview: rawText.slice(0, 180),
    recommended: sorted[0],
    alternatives: sorted.slice(1, 3),
  };
}

function normaliza(value) {
  return value
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function splitTokens(value) {
  return value
    .split(/\s+/)
    .filter(Boolean);
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function readAgentId(args) {
  const envAgent = Number(process.env.MODEL_ROUTER_AGENT_ID) || 1;
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === '--agent') {
      return Number(args[index + 1]) || envAgent;
    }
    if (arg.startsWith('--agent=')) {
      return Number(arg.slice('--agent='.length)) || envAgent;
    }
  }
  return envAgent;
}

function getAgentBoost(modelId, agentId) {
  const normalizedAgent = Number(agentId) || 1;
  const modelIndex = MODEL_MATRIX.findIndex((entry) => entry.id === modelId);
  const preference = normalizedAgent % MODEL_MATRIX.length === modelIndex ? 2.4 : 0;
  const hash = hashString(`agent:${normalizedAgent}:${modelId}`);
  const jitter = ((hash % 9) - 4) / 3;
  return preference + jitter;
}

function hashString(value) {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function printHelp() {
  const usage = `Uso:
  npm run model:guide [--json]
  node scripts/model-router.mjs --guide [--json]
  node scripts/model-router.mjs "texto de tarea"
  node scripts/model-router.mjs --json "texto de tarea"

Resultado:
  Imprime el modelo sugerido para el texto entrante (sin necesidad de intervención manual).

Modelos:
  - gpt-5.4
  - gpt-5.4-Mini
  - gpt-5.3-codex
  - gpt-5.3-codex-spark
  - gpt-5.2`;
  process.stdout.write(`${usage}\n`);
}

function printGuide(wantsJson) {
  const guidance = MODEL_MATRIX.map((model) => ({
    id: model.id,
    name: model.name,
    mejor_para: model.focus,
    señales: model.signals.slice(0, 10),
  }));

  if (wantsJson) {
    process.stdout.write(JSON.stringify({ modelos: guidance }, null, 2));
    process.stdout.write('\n');
    return;
  }

  process.stdout.write('Guía de uso por modelo:\n');
  for (const entry of guidance) {
    process.stdout.write(`- ${entry.id}: ${entry.mejor_para}\n`);
    process.stdout.write(`  Señales típicas: ${entry.señales.join(', ')}\n`);
  }
}
