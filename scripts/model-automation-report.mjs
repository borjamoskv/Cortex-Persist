#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { resolveLedgerConfig } from './model-automation-ledger.mjs';

const argv = process.argv.slice(2);
const parsed = parseArguments(argv);

if (parsed.help) {
  process.stdout.write(`${buildUsage()}\n`);
  process.exit(0);
}

if (parsed.error) {
  emitError(parsed.error, parsed.json);
  process.exit(1);
}

const ledgerPath = parsed.path
  ? (path.isAbsolute(parsed.path) ? parsed.path : path.resolve(process.cwd(), parsed.path))
  : resolveLedgerConfig(process.env, process.cwd()).path;

const report = buildReport({
  ledgerPath,
  includeRotated: parsed.includeRotated,
  limit: parsed.limit,
  filters: parsed.filters,
});

if (parsed.json) {
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  process.exit(0);
}

process.stdout.write(`${renderReport(report)}\n`);
process.exit(0);

function buildReport({ ledgerPath, includeRotated, limit, filters }) {
  const loaded = loadLedgerEntries({ ledgerPath, includeRotated });
  const filteredEntries = loaded.entries.filter((entry) => matchesFilters(entry, filters));
  const runs = summarizeRuns(filteredEntries).slice(0, limit);

  return {
    status: filteredEntries.length ? 'ok' : 'empty',
    ledgerPath,
    includeRotated,
    filters,
    files: loaded.files,
    parseErrors: loaded.parseErrors,
    totals: summarizeTotals(filteredEntries),
    byStatus: summarizeCounts(filteredEntries, 'status'),
    byFlow: summarizeCounts(filteredEntries, 'flow'),
    byModel: summarizeCounts(filteredEntries, 'model'),
    runs,
  };
}

function loadLedgerEntries({ ledgerPath, includeRotated }) {
  const filePaths = includeRotated ? [`${ledgerPath}.1`, ledgerPath] : [ledgerPath];
  const files = [];
  const entries = [];
  const parseErrors = [];

  for (const filePath of filePaths) {
    if (!fs.existsSync(filePath)) {
      files.push({
        path: filePath,
        exists: false,
        entries: 0,
        parseErrors: 0,
      });
      continue;
    }

    const fileEntries = [];
    let fileParseErrors = 0;
    const lines = fs.readFileSync(filePath, 'utf8')
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);

    for (const line of lines) {
      try {
        fileEntries.push(JSON.parse(line));
      } catch (error) {
        fileParseErrors += 1;
        parseErrors.push({
          path: filePath,
          message: error instanceof Error ? error.message : String(error),
        });
      }
    }

    files.push({
      path: filePath,
      exists: true,
      entries: fileEntries.length,
      parseErrors: fileParseErrors,
    });
    entries.push(...fileEntries);
  }

  return { files, entries, parseErrors };
}

function matchesFilters(entry, filters) {
  if (filters.runId && entry.runId !== filters.runId) return false;
  if (filters.flow && entry.flow !== filters.flow) return false;
  if (filters.status && entry.status !== filters.status) return false;
  if (filters.model && entry.model !== filters.model) return false;
  if (filters.source && entry.source !== filters.source) return false;
  return true;
}

function summarizeTotals(entries) {
  const completedEntries = entries.filter((entry) => entry.status === 'ok' || entry.status === 'failed');
  const okEntries = completedEntries.filter((entry) => entry.status === 'ok').length;

  return {
    entries: entries.length,
    runs: new Set(entries.map((entry) => entry.runId).filter(Boolean)).size,
    completedEntries: completedEntries.length,
    okEntries,
    failedEntries: completedEntries.filter((entry) => entry.status === 'failed').length,
    successRate: completedEntries.length ? roundMetric(okEntries / completedEntries.length) : null,
    averageTotalMs: averageNumeric(entries.map((entry) => entry.timing?.totalMs)),
    averageRouterMs: averageNumeric(entries.map((entry) => entry.timing?.routerMs ?? entry.timing?.routerTotalMs)),
    averageExecutionMs: averageNumeric(entries.map((entry) => entry.timing?.executionMs)),
  };
}

function summarizeCounts(entries, field) {
  return Object.entries(
    entries.reduce((acc, entry) => {
      const value = normalizeCountKey(entry[field]);
      if (!value) return acc;
      acc[value] = (acc[value] || 0) + 1;
      return acc;
    }, {}),
  )
    .map(([value, count]) => ({ [field]: value, count }))
    .sort((a, b) => {
      if (b.count !== a.count) return b.count - a.count;
      return String(a[field]).localeCompare(String(b[field]));
    });
}

function summarizeRuns(entries) {
  const groups = new Map();

  for (const entry of entries) {
    const groupKey = String(entry.runId || `sin-run-id:${entry.timestamp || Math.random()}`);
    if (!groups.has(groupKey)) {
      groups.set(groupKey, []);
    }
    groups.get(groupKey).push(entry);
  }

  return Array.from(groups.entries())
    .map(([runId, runEntries]) => {
      const sorted = [...runEntries].sort((a, b) => getTimestampValue(b.timestamp) - getTimestampValue(a.timestamp));
      const latest = sorted[0] || {};
      return {
        runId,
        entries: runEntries.length,
        latestTimestamp: latest.timestamp || null,
        status: latest.status || null,
        flow: latest.flow || null,
        model: latest.model || null,
        sources: uniqueValues(runEntries.map((entry) => entry.source)),
        statuses: uniqueValues(runEntries.map((entry) => entry.status)),
        flows: uniqueValues(runEntries.map((entry) => entry.flow)),
        models: uniqueValues(runEntries.map((entry) => entry.model)),
        averageTotalMs: averageNumeric(runEntries.map((entry) => entry.timing?.totalMs)),
        averageExecutionMs: averageNumeric(runEntries.map((entry) => entry.timing?.executionMs)),
      };
    })
    .sort((a, b) => getTimestampValue(b.latestTimestamp) - getTimestampValue(a.latestTimestamp));
}

function averageNumeric(values) {
  const valid = values.filter((value) => Number.isFinite(value));
  if (!valid.length) {
    return null;
  }
  return roundMetric(valid.reduce((sum, value) => sum + value, 0) / valid.length);
}

function uniqueValues(values) {
  return Array.from(new Set(values.filter(Boolean))).sort();
}

function normalizeCountKey(value) {
  const normalized = String(value || '').trim();
  return normalized || '';
}

function getTimestampValue(value) {
  const parsed = Date.parse(String(value || ''));
  return Number.isFinite(parsed) ? parsed : 0;
}

function roundMetric(value) {
  return Math.round(value * 1000) / 1000;
}

function parseArguments(rawArgs) {
  const control = {
    json: false,
    help: false,
    includeRotated: true,
    limit: 10,
    path: '',
    filters: {
      runId: '',
      flow: '',
      status: '',
      model: '',
      source: '',
    },
  };

  for (let index = 0; index < rawArgs.length; index += 1) {
    const arg = rawArgs[index];
    if (arg === '--json') {
      control.json = true;
      continue;
    }
    if (arg === '--help' || arg === '-h') {
      control.help = true;
      continue;
    }
    if (arg === '--no-rotate') {
      control.includeRotated = false;
      continue;
    }
    if (arg === '--path') {
      const value = rawArgs[index + 1];
      if (!value) return { ...control, error: { code: 'flag_incompleto', flag: '--path' } };
      control.path = value;
      index += 1;
      continue;
    }
    if (arg.startsWith('--path=')) {
      control.path = arg.slice('--path='.length);
      continue;
    }
    if (arg === '--limit') {
      const value = rawArgs[index + 1];
      if (!value) return { ...control, error: { code: 'flag_incompleto', flag: '--limit' } };
      control.limit = parsePositiveInt(value, 10);
      index += 1;
      continue;
    }
    if (arg.startsWith('--limit=')) {
      control.limit = parsePositiveInt(arg.slice('--limit='.length), 10);
      continue;
    }

    const filterMatch = arg.match(/^--(run-id|flow|status|model|source)=(.+)$/);
    if (filterMatch) {
      control.filters[toFilterKey(filterMatch[1])] = filterMatch[2].trim();
      continue;
    }
    if (['--run-id', '--flow', '--status', '--model', '--source'].includes(arg)) {
      const value = rawArgs[index + 1];
      if (!value) return { ...control, error: { code: 'flag_incompleto', flag: arg } };
      control.filters[toFilterKey(arg.slice(2))] = value.trim();
      index += 1;
      continue;
    }
    if (arg.startsWith('-')) {
      return { ...control, error: { code: 'flag_desconocido', flag: arg } };
    }
    return { ...control, error: { code: 'argumento_desconocido', value: arg } };
  }

  return control;
}

function toFilterKey(value) {
  return value === 'run-id' ? 'runId' : value;
}

function parsePositiveInt(value, fallback) {
  const parsed = parseInt(String(value || '').trim(), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function emitError(error, wantsJson) {
  const payload = {
    error: error.code,
    ...(error.flag ? { flag: error.flag } : {}),
    ...(error.value ? { value: error.value } : {}),
    usage: 'npm run model:ledger -- --json [--path ruta] [--run-id id] [--flow flow] [--no-rotate]',
  };

  if (wantsJson) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return;
  }

  process.stderr.write(`${payload.error}${payload.flag ? ` (${payload.flag})` : ''}\n`);
  process.stderr.write(`${payload.usage}\n`);
}

function renderReport(report) {
  const lines = [
    `Ledger: ${report.ledgerPath}`,
    `Estado: ${report.status}`,
    `Entradas: ${report.totals.entries} | Runs: ${report.totals.runs} | Completadas: ${report.totals.completedEntries}`,
    `Success rate: ${report.totals.successRate === null ? 'n/a' : `${Math.round(report.totals.successRate * 100)}%`}`,
    `Media ms: total=${formatMetric(report.totals.averageTotalMs)} router=${formatMetric(report.totals.averageRouterMs)} exec=${formatMetric(report.totals.averageExecutionMs)}`,
  ];

  if (report.byStatus.length) {
    lines.push(`Estados: ${renderCountLine(report.byStatus, 'status')}`);
  }
  if (report.byFlow.length) {
    lines.push(`Flujos: ${renderCountLine(report.byFlow, 'flow')}`);
  }
  if (report.byModel.length) {
    lines.push(`Modelos: ${renderCountLine(report.byModel, 'model')}`);
  }
  if (report.runs.length) {
    lines.push('Runs recientes:');
    for (const run of report.runs) {
      lines.push(`- ${run.runId} | ${run.latestTimestamp || 'sin timestamp'} | status=${run.status || 'n/a'} flow=${run.flow || 'n/a'} model=${run.model || 'n/a'} entries=${run.entries}`);
    }
  }
  if (report.parseErrors.length) {
    lines.push(`Parse errors: ${report.parseErrors.length}`);
  }

  return lines.join('\n');
}

function renderCountLine(entries, field) {
  return entries.map((entry) => `${entry[field]} ${entry.count}`).join(' | ');
}

function formatMetric(value) {
  return value === null ? 'n/a' : String(value);
}

function buildUsage() {
  return [
    'Uso:',
    '  npm run model:ledger -- --json',
    '  npm run model:ledger -- --flow=swarm --limit=5',
    '  npm run model:ledger -- --run-id=<runId> --path .cortex/model-automation-ledger.jsonl',
    '',
    'Flags:',
    '  --json           salida estructurada',
    '  --path           ruta explícita al ledger JSONL',
    '  --run-id         filtra por ejecución',
    '  --flow           filtra por flujo',
    '  --status         filtra por estado',
    '  --model          filtra por modelo',
    '  --source         filtra por fuente',
    '  --limit          máximo de runs en el resumen (default 10)',
    '  --no-rotate      ignora el backup rotado (*.1)',
  ].join('\n');
}
