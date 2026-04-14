#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import { maybeWriteAutomationLedger, resolveAutomationRunId } from './model-automation-ledger.mjs';

const nodePath = process.execPath;
const scriptsRoot = process.cwd();
const swarmStartedAt = Date.now();
const runId = resolveAutomationRunId(process.env);

const argv = process.argv.slice(2);
if (argv.includes('--help') || argv.includes('-h')) {
  printUsage();
  process.exit(0);
}

const parsed = parseArguments(argv);
const taskPrompt = normalizeTaskText(getTaskPrompt(parsed.taskPromptInput));
const taskError = getTaskValidationError(taskPrompt);
if (taskError) {
  emitTaskError(parsed.json, taskError);
  process.exit(1);
}

const recommendationPlan = [];
const modelStats = {};
let routerTotalMs = 0;

for (let agentIndex = 1; agentIndex <= parsed.agents; agentIndex += 1) {
  const { decision, routerMs } = runRouter(taskPrompt, agentIndex);
  const model = decision.recommended.id;
  const confidence = decision.recommended.confidence || 0;
  recommendationPlan.push({
    agent: agentIndex,
    model: decision.recommended.id,
    confidence,
    routerMs,
    reason: decision.recommended.reason || '',
  });
  routerTotalMs += routerMs;
  modelStats[model] = modelStats[model] || { count: 0, confidenceTotal: 0 };
  modelStats[model].count += 1;
  modelStats[model].confidenceTotal += confidence;
}

const rankedModels = Object.entries(modelStats)
  .map(([model, stats]) => ({
    model,
    count: stats.count,
    averageConfidence: stats.count ? roundMetric(stats.confidenceTotal / stats.count) : 0,
  }))
  .sort((a, b) => {
    if (b.count !== a.count) return b.count - a.count;
    return b.averageConfidence - a.averageConfidence;
  });
const winner = rankedModels[0];
if (!winner) {
  process.stderr.write('model swarm failed: no se pudo calcular un ganador.\n');
  process.exit(1);
}

const commandPlan = buildCommandPlan({
  taskPrompt,
  parsed,
});

if (!commandPlan.shouldExecute) {
  const summary = finalizeSwarmSummary(buildSummary({
    winner,
    recommendationPlan,
    commandPlan,
    status: parsed.dryRun ? 'dry-run' : 'planned',
  }), taskPrompt);
  emitSummary(parsed.json, summary);
  process.exit(0);
}

if (parsed.dryRun) {
  const summary = finalizeSwarmSummary(buildSummary({
    winner,
    recommendationPlan,
    commandPlan,
    status: 'dry-run',
  }), taskPrompt);
  emitSummary(parsed.json, summary);
  process.exit(0);
}

const commandEnv = {
  ...process.env,
  MODEL_AUTOMATION_RUN_ID: runId,
  CODEX_MODEL: winner.model,
  MODEL_DISPATCH: winner.model,
  MODEL_ROUTER_SELECTION: winner.model,
  MODEL_SWARM_AGENTS: String(recommendationPlan.length),
  MODEL_SWARM_CONSENSUS_MODEL: winner.model,
  MODEL_SWARM_CONSENSUS_RATIO: String(roundMetric(winner.count / recommendationPlan.length)),
  MODEL_TASK_TEXT: taskPrompt,
  TASK_TEXT: taskPrompt,
};
const executionStartedAt = Date.now();
const execution = spawnSync(commandPlan.command, {
  shell: true,
  cwd: scriptsRoot,
  stdio: 'inherit',
  env: commandEnv,
});
const executionDurationMs = Date.now() - executionStartedAt;

if (execution.error || execution.status) {
  const exitCode = execution.error ? 1 : execution.status;
  const summary = finalizeSwarmSummary(buildSummary({
    winner,
    recommendationPlan,
    commandPlan,
    status: 'failed',
    executed: commandPlan.command,
    exitCode,
    reason: execution.error?.message || `command exited with ${exitCode}`,
    executionMs: executionDurationMs,
  }), taskPrompt);
  emitSummary(parsed.json, summary);
  process.exit(exitCode || 1);
}

const summary = finalizeSwarmSummary(buildSummary({
  winner,
  recommendationPlan,
  commandPlan,
  status: 'ok',
  executed: commandPlan.command,
  executionMs: executionDurationMs,
}), taskPrompt);
emitSummary(parsed.json, summary);
process.exit(0);

function runRouter(taskText, agentIndex) {
  const routerPath = path.resolve(scriptsRoot, 'scripts', 'model-router.mjs');
  const routerStartedAt = Date.now();
  const router = spawnSync(nodePath, [routerPath, '--json', taskText], {
    encoding: 'utf8',
    cwd: scriptsRoot,
    env: {
      ...process.env,
      MODEL_ROUTER_AGENT_ID: String(agentIndex),
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const routerDurationMs = Date.now() - routerStartedAt;

  if (router.status !== 0 || !router.stdout) {
    process.stderr.write(`model swarm failed: router returned status ${router.status || 0}\n`);
    if (router.stderr?.trim()) {
      process.stderr.write(router.stderr);
    }
    process.exit(router.status || 1);
  }

  try {
    return {
      decision: JSON.parse(router.stdout),
      routerMs: routerDurationMs,
    };
  } catch (error) {
    process.stderr.write(`model swarm failed: invalid router payload (${error.message})\n`);
    process.exit(1);
  }
}

function buildCommandPlan({ taskPrompt, parsed }) {
  const envFlow = process.env.TASK_FLOW || process.env.CODEX_FLOW || process.env.MODEL_ROUTER_FLOW;
  const requestedFlow = parsed.flow || envFlow || '';
  const explicitCommand = collectCommandFromArgs(parsed.commandArgs);
  const envCommand = (
    process.env.TASK_COMMAND
    || process.env.CODEX_TASK_COMMAND
    || process.env.MODEL_ROUTER_COMMAND
    || ''
  ).trim();

  if (explicitCommand) {
    return {
      shouldExecute: true,
      flow: requestedFlow || 'custom',
      command: explicitCommand,
    };
  }

  if (envCommand) {
    return {
      shouldExecute: true,
      flow: requestedFlow || 'custom',
      command: envCommand,
    };
  }

  if (requestedFlow === 'swarm') {
    return {
      shouldExecute: false,
      flow: 'swarm',
      command: '',
      guardedReason: 'recursive_swarm_flow',
    };
  }

  if (!requestedFlow && !parsed.auto) {
    return {
      shouldExecute: false,
      flow: '',
      command: '',
    };
  }

  const dispatcherPath = path.resolve(scriptsRoot, 'scripts', 'model-dispatcher.mjs');
  const dryArgs = ['--dry-run', '--json'];
  if (parsed.auto) {
    dryArgs.push('--auto');
  }
  if (requestedFlow) {
    dryArgs.push(`--flow=${requestedFlow}`);
  }
  dryArgs.push(taskPrompt);
  const dispatchRun = spawnSync(nodePath, [dispatcherPath, ...dryArgs], {
    encoding: 'utf8',
    cwd: scriptsRoot,
    env: {
      ...process.env,
      MODEL_ROUTER_COMMAND: 'echo',
      TASK_COMMAND: '',
      CODEX_TASK_COMMAND: '',
      TASK_FLOW: requestedFlow || '',
    },
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  if (dispatchRun.status !== 0 || !dispatchRun.stdout) {
    return {
      shouldExecute: false,
      flow: requestedFlow || '',
      command: '',
    };
  }

  try {
    const payload = JSON.parse(dispatchRun.stdout.trim());
    const command = payload && payload.command ? payload.command : '';
    return {
      shouldExecute: Boolean(command),
      flow: requestedFlow || payload.flow || '',
      command,
    };
  } catch {
    return {
      shouldExecute: false,
      flow: requestedFlow || '',
      command: '',
    };
  }
}

function buildSummary({
  winner,
  recommendationPlan,
  commandPlan,
  status,
  executed,
  exitCode,
  reason,
  executionMs = 0,
}) {
  const totalConfidence = recommendationPlan.reduce((sum, entry) => sum + (entry.confidence || 0), 0);
  const modelBreakdown = Object.entries(
    recommendationPlan.reduce((acc, entry) => {
      if (!acc[entry.model]) {
        acc[entry.model] = { count: 0, confidenceTotal: 0 };
      }
      acc[entry.model].count += 1;
      acc[entry.model].confidenceTotal += entry.confidence || 0;
      return acc;
    }, {}),
  )
    .map(([model, stats]) => ({
      model,
      count: stats.count,
      averageConfidence: stats.count ? roundMetric(stats.confidenceTotal / stats.count) : 0,
    }))
    .sort((a, b) => {
      if (b.count !== a.count) return b.count - a.count;
      return b.averageConfidence - a.averageConfidence;
    });

  return {
    engine: 'swarm',
    status,
    agents: recommendationPlan.length,
    consensus: winner,
    consensusRatio: recommendationPlan.length ? roundMetric(winner.count / recommendationPlan.length) : 0,
    averageConfidence: recommendationPlan.length ? roundMetric(totalConfidence / recommendationPlan.length) : 0,
    modelBreakdown,
    recommendations: recommendationPlan,
    command: commandPlan.command,
    flow: commandPlan.flow,
    shouldExecute: commandPlan.shouldExecute,
    guardedReason: commandPlan.guardedReason,
    taskMetrics: buildTaskMetrics(taskPrompt),
    timing: {
      totalMs: Date.now() - swarmStartedAt,
      routerTotalMs,
      routerAverageMs: recommendationPlan.length ? roundMetric(routerTotalMs / recommendationPlan.length) : 0,
      executionMs,
    },
    executed,
    exitCode,
    reason,
  };
}

function emitSummary(wantsJson, summary) {
  if (!wantsJson) {
    process.stdout.write(`[swarm] agents=${summary.agents} status=${summary.status}\n`);
    process.stdout.write(`[swarm] consensus=${summary.consensus.model} x${summary.consensus.count}\n`);
    if (summary.command) {
      process.stdout.write(`[swarm] command=${summary.command}\n`);
    }
    process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
    return;
  }
  process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
}

function collectCommandFromArgs(commandArgs) {
  return commandArgs.join(' ').trim();
}

function parseArguments(rawArgs) {
  const parts = [];
  const control = {
    json: false,
    dryRun: false,
    auto: false,
    flow: '',
    agents: parseInt(process.env.MODEL_SWARM_AGENTS || '21', 10) || 21,
  };
  const separator = rawArgs.indexOf('--');
  const options = separator === -1 ? rawArgs : rawArgs.slice(0, separator);
  const commandArgsInput = separator === -1 ? [] : rawArgs.slice(separator + 1);

  for (let index = 0; index < options.length; index += 1) {
    const arg = options[index];
    if (arg === '--json') {
      control.json = true;
      continue;
    }
    if (arg === '--dry-run') {
      control.dryRun = true;
      continue;
    }
    if (arg === '--auto') {
      control.auto = true;
      continue;
    }
    if (arg === '--agents' && options[index + 1]) {
      control.agents = clampAgents(parseInt(options[index + 1], 10));
      index += 1;
      continue;
    }
    if (arg.startsWith('--agents=')) {
      control.agents = clampAgents(parseInt(arg.slice('--agents='.length), 10));
      continue;
    }
    if (arg === '--flow') {
      control.flow = options[index + 1] || '';
      index += 1;
      continue;
    }
    if (arg.startsWith('--flow=')) {
      control.flow = arg.slice('--flow='.length);
      continue;
    }
    if (arg.startsWith('-')) {
      continue;
    }
    parts.push(arg);
  }

  const fromEnv = (process.env.MODEL_SWARM_AGENTS || '').trim();
  if (!Number.isNaN(parseInt(fromEnv, 10)) && fromEnv) {
    control.agents = clampAgents(parseInt(fromEnv, 10));
  }

  return {
    ...control,
    taskPromptInput: parts,
    commandArgs: commandArgsInput,
  };
}

function getTaskPrompt(taskPromptInput) {
  if (taskPromptInput.length) {
    return taskPromptInput.join(' ').trim();
  }
  const envTaskText = (process.env.MODEL_SWARM_TASK_TEXT || process.env.MODEL_TASK_TEXT || process.env.TASK_TEXT || '').trim();
  if (envTaskText) {
    return envTaskText;
  }
  try {
    return fs.readFileSync(0, 'utf8').toString().trim();
  } catch {
    return '';
  }
}

function clampAgents(value) {
  if (!Number.isFinite(value)) return 21;
  return Math.min(100, Math.max(1, value));
}

function normalizeTaskText(value) {
  return value.replace(/\s+/g, ' ').trim();
}

function getTaskValidationError(taskText) {
  if (!taskText) {
    return {
      code: 'tarea_vacia',
      message: 'texto de tarea vacío. Pasa un texto como argumento, entorno o stdin.',
    };
  }
  const maxChars = parseInt(process.env.MODEL_MAX_TASK_CHARS || '8000', 10);
  if (taskText.length > maxChars) {
    return {
      code: 'tarea_demasiado_larga',
      message: `texto de tarea demasiado largo (${taskText.length}/${maxChars}). Reduce el prompt o ajusta MODEL_MAX_TASK_CHARS.`,
    };
  }
  return null;
}

function emitTaskError(wantsJson, taskError) {
  if (wantsJson) {
    process.stdout.write(`${JSON.stringify(taskError, null, 2)}\n`);
    return;
  }
  printUsage();
}

function buildTaskMetrics(taskText) {
  return {
    characters: taskText.length,
    words: taskText ? taskText.split(/\s+/).filter(Boolean).length : 0,
  };
}

function roundMetric(value) {
  return Math.round(value * 1000) / 1000;
}

function finalizeSwarmSummary(summary, taskPrompt) {
  const summaryWithRunId = {
    runId,
    ...summary,
  };
  const ledger = persistSwarmLedger(summary, taskPrompt);
  if (ledger.enabled) {
    return {
      ...summaryWithRunId,
      ledger,
    };
  }
  return summaryWithRunId;
}

function persistSwarmLedger(summary, taskPrompt) {
  const entry = stripUndefined({
    runId,
    source: 'model-swarm',
    engine: 'swarm',
    status: summary.status,
    flow: summary.flow,
    model: summary.consensus?.model,
    agents: summary.agents,
    consensus: summary.consensus,
    consensusRatio: summary.consensusRatio,
    averageConfidence: summary.averageConfidence,
    taskPreview: buildTaskPreview(taskPrompt),
    taskMetrics: summary.taskMetrics,
    timing: summary.timing,
    executed: summary.executed,
    exitCode: summary.exitCode,
    reason: summary.reason,
    guardedReason: summary.guardedReason,
  });

  return maybeWriteAutomationLedger(entry, process.env, process.cwd());
}

function buildTaskPreview(taskText) {
  return taskText.length <= 180 ? taskText : `${taskText.slice(0, 177)}...`;
}

function stripUndefined(value) {
  return Object.fromEntries(
    Object.entries(value).filter(([, entry]) => entry !== undefined),
  );
}

function printUsage() {
  const lines = [
    'Uso:',
    '  node scripts/model-swarm.mjs [--agents=21] [--dry-run] [--json] "texto de tarea"',
    '  TASK_COMMAND="npm run build" TASK_FLOW=web npm run model:swarm -- --json "Texto de tarea"',
    '  echo "Texto de tarea" | node scripts/model-swarm.mjs --dry-run --auto --flow=web',
    '',
    'Salida JSON:',
    '  - engine: "swarm"',
    '  - agents: número de agentes usados',
    '  - consensus: modelo ganador y conteo',
  ];
  process.stdout.write(`${lines.join('\n')}\n`);
}
