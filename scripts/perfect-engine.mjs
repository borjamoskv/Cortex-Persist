#!/usr/bin/env node

import { spawnSync } from 'node:child_process';

const args = process.argv.slice(2);
const wantsJson = args.includes('--json');
const wantsDryRun = args.includes('--dry-run');

if (args.includes('--help') || args.includes('-h')) {
  printUsage();
  process.exit(0);
}

const repoRoot = process.cwd();
const steps = buildSteps(repoRoot);
const summary = {
  engine: 'perfect',
  repoRoot,
  status: 'ok',
  dryRun: wantsDryRun,
  steps: [],
  timestamp: new Date().toISOString(),
};

if (wantsDryRun) {
  summary.steps = steps.map((step) => serializeDryRunStep(step));
  emitSummary(summary);
  process.exit(0);
}

const remaining = [...steps];
while (remaining.length) {
  const step = remaining.shift();
  if (!step) break;

  if (!step.enabled) {
    summary.steps.push({
      id: step.id,
      name: step.name,
      command: step.command,
      required: step.required,
      status: 'skipped',
      durationMs: 0,
      detail: step.skipReason,
    });
    continue;
  }

  logStep(step);
  const startedAt = Date.now();
  const run = spawnSync(step.command, {
    cwd: repoRoot,
    shell: true,
    stdio: 'inherit',
    env: process.env,
  });
  const durationMs = Date.now() - startedAt;
  const exitCode = run.error ? 1 : (run.status ?? 0);
  const passed = !run.error && exitCode === 0;

  summary.steps.push({
    id: step.id,
    name: step.name,
    command: step.command,
    required: step.required,
    status: passed ? 'ok' : 'failed',
    exitCode,
    durationMs,
    detail: passed ? step.successDetail : (run.error?.message || `command exited with status ${exitCode}`),
  });

  if (!passed) {
    summary.status = 'failed';
    summary.steps.push(
      ...remaining.map((pending) => ({
        id: pending.id,
        name: pending.name,
        command: pending.command,
        required: pending.required,
        status: 'blocked',
        durationMs: 0,
        detail: `blocked after ${step.id} failed`,
      })),
    );
    emitSummary(summary);
    process.exit(exitCode || 1);
  }
}

emitSummary(summary);
process.exit(0);

/**
 * Build the sequence of validation engines that define the "perfect" workflow.
 */
function buildSteps(repoRootPath) {
  const python = process.env.PYTHON || 'python3';
  const shipGateOverride = readOverride('CORTEX_PERFECT_SHIP_GATE_CMD');

  return [
    {
      id: 'repo-health',
      name: 'Repo health',
      command: readOverride('CORTEX_PERFECT_REPO_HEALTH_CMD') || `${python} scripts/repo_health_changed.py --all`,
      required: true,
      enabled: true,
      skipReason: '',
      successDetail: 'merge markers and Python syntax look clean',
    },
    {
      id: 'model-tests',
      name: 'Model automation tests',
      command: readOverride('CORTEX_PERFECT_MODEL_TESTS_CMD') || 'npm run test:models',
      required: true,
      enabled: true,
      skipReason: '',
      successDetail: 'local model automation regression suite passed',
    },
    {
      id: 'web-build',
      name: 'Astro build',
      command: readOverride('CORTEX_PERFECT_BUILD_CMD') || 'npm run build',
      required: true,
      enabled: true,
      skipReason: '',
      successDetail: 'production build completed',
    },
    {
      id: 'ship-gate',
      name: 'Python ship gate',
      command: shipGateOverride || `${python} scripts/ship_gate.py --fast --json-only`,
      required: true,
      enabled: true,
      skipReason: '',
      successDetail: 'fast ship gate passed',
    },
  ];
}

function readOverride(envName) {
  const value = process.env[envName];
  return typeof value === 'string' && value.trim() ? value.trim() : '';
}

function serializeDryRunStep(step) {
  return {
    id: step.id,
    name: step.name,
    command: step.command,
    required: step.required,
    status: step.enabled ? 'planned' : 'skipped',
    durationMs: 0,
    detail: step.enabled ? 'dry-run' : step.skipReason,
  };
}

function logStep(step) {
  if (wantsJson) return;
  process.stdout.write(`[perfect] ${step.id}: ${step.name}\n`);
}

function emitSummary(summary) {
  if (!wantsJson) {
    process.stdout.write(`[perfect] status=${summary.status}\n`);
  }
  process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
}

function printUsage() {
  const lines = [
    'Uso:',
    '  npm run engine:perfect',
    '  npm run engine:perfect -- --dry-run --json',
    '',
    'Motores incluidos:',
    '  - repo health (merge markers + sintaxis Python)',
    '  - test:models',
    '  - build web',
    '  - ship gate Python (si la toolchain local existe)',
  ];
  process.stdout.write(`${lines.join('\n')}\n`);
}
