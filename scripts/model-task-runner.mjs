#!/usr/bin/env node

/**
 * Ejecuta el dispatcher con un flujo predefinido y un texto de tarea.
 * Uso:
 *   node scripts/model-task-runner.mjs build "texto"
 *   npm run task:build -- "texto"
 */
import { spawnSync } from 'node:child_process';
import * as path from 'node:path';
import * as fs from 'node:fs';

const SUPPORTED_FLOWS = ['auto', 'build', 'release', 'ship', 'web', 'test', 'swarm', 'perfect'];

const args = process.argv.slice(2);
if (args.includes('--help') || args.includes('-h') || args.length === 0) {
  printUsage();
  process.exit(args.length === 0 ? 1 : 0);
}

const lifecycleFlow = getLifecycleFlow();
const parsed = parseArgs(args);
if (parsed.error) {
  emitParseError(parsed);
  process.exit(1);
}
let flow = parsed.flow || lifecycleFlow;
let taskPrompt = parsed.taskPrompt.trim();

if (
  parsed.forceFlowFromPrompt
  || (lifecycleFlow && parsed.firstToken === lifecycleFlow)
) {
  taskPrompt = parsed.taskFromFlowAwarePrompt.trim();
}

if (!flow && !lifecycleFlow && !parsed.forceFlowFromPrompt) {
  flow = 'auto';
} else if (!flow && parsed.forceFlowFromPrompt) {
  flow = parsed.firstToken;
}

if (!SUPPORTED_FLOWS.includes(flow)) {
  process.stderr.write(`model task runner failed: flujo desconocido '${flow || '<vacío>'}'. Usa uno de: ${SUPPORTED_FLOWS.join(', ')}\n`);
  process.exit(1);
}

if (!taskPrompt && !lifecycleFlow) {
  taskPrompt = parsed.taskFromFlowAwarePrompt.trim();
}

const wantsJson = parsed.wantsJson;
const wantsDryRun = parsed.wantsDryRun;
const agents = parsed.agents;
if (!taskPrompt) {
  taskPrompt = fs.readFileSync(0, 'utf8').toString().trim();
}

if (!taskPrompt) {
  printUsage();
  process.exit(1);
}

const dispatcher = path.resolve(process.cwd(), 'scripts/model-dispatcher.mjs');
const runnerArgs = ['--auto'];
if (flow !== 'auto') {
  runnerArgs.push(`--flow=${flow}`);
}
if (wantsJson) {
  runnerArgs.push('--json');
}
if (wantsDryRun) {
  runnerArgs.push('--dry-run');
}
if (flow === 'swarm' && agents) {
  runnerArgs.push(`--agents=${agents}`);
}
runnerArgs.push(taskPrompt);

const run = spawnSync(process.execPath, [dispatcher, ...runnerArgs], {
  stdio: 'inherit',
});

if (run.error) {
  process.stderr.write(`model task runner failed: ${run.error.message}\n`);
  process.exit(1);
}

process.exit(run.status ?? 0);

function printUsage() {
  const lines = [
    'Uso:',
    '  npm run task:build -- "Texto de tarea"',
    '  npm run task:web -- --json "Texto de tarea"  # opción JSON',
    '  npm run task:swarm -- --agents=21 --json "Texto de tarea"  # usa 21 agentes',
    '  npm run task:perfect -- --json "Blindar y dejar el repo perfecto"',
    '  echo "Texto de tarea" | npm run task:web -- --json',
    `Flujos soportados: ${SUPPORTED_FLOWS.join(', ')}`,
  ];
  process.stdout.write(`${lines.join('\n')}\n`);
}

function parseArgs(argv) {
  const result = {
    flow: '',
    wantsJson: false,
    wantsDryRun: false,
    agents: 0,
    taskPrompt: '',
    taskFromFlowAwarePrompt: '',
    forceFlowFromPrompt: false,
    firstToken: '',
    error: null,
  };

  const parts = [];
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') {
      printUsage();
      process.exit(0);
    }

    if (arg === '--json') {
      result.wantsJson = true;
      continue;
    }

    if (arg === '--dry-run') {
      result.wantsDryRun = true;
      continue;
    }

    if (arg === '--agents' && argv[i + 1] && !argv[i + 1].startsWith('-')) {
      const value = argv[i + 1];
      const parsedAgents = parseAgentsValue(value);
      if (!parsedAgents) {
        result.error = buildParseError('flag_invalido', '--agents', value);
        break;
      }
      result.agents = parsedAgents;
      i += 1;
      continue;
    }

    if (arg === '--agents') {
      result.error = buildParseError('flag_incompleto', '--agents');
      break;
    }

    if (arg.startsWith('--agents=')) {
      const value = arg.slice('--agents='.length);
      const parsedAgents = parseAgentsValue(value);
      if (!parsedAgents) {
        result.error = buildParseError('flag_invalido', '--agents', value);
        break;
      }
      result.agents = parsedAgents;
      continue;
    }

    if (arg.startsWith('--flow=')) {
      const value = arg.slice('--flow='.length).trim();
      if (!value) {
        result.error = buildParseError('flag_incompleto', '--flow');
        break;
      }
      result.flow = value;
      continue;
    }

    if (arg === '--flow' && argv[i + 1] && !argv[i + 1].startsWith('-')) {
      result.flow = argv[i + 1];
      i += 1;
      continue;
    }

    if (arg === '--flow') {
      result.error = buildParseError('flag_incompleto', '--flow');
      break;
    }

    if (arg.startsWith('-') || arg === '') {
      continue;
    }

    parts.push(arg);
  }

  result.taskPrompt = parts.join(' ');
  result.taskFromFlowAwarePrompt = parts[0] === result.flow ? parts.slice(1).join(' ') : result.taskPrompt;
  result.firstToken = parts[0] || '';

  if (!result.flow && result.firstToken && SUPPORTED_FLOWS.includes(result.firstToken)) {
    result.forceFlowFromPrompt = true;
    result.flow = result.firstToken;
    result.taskFromFlowAwarePrompt = parts.slice(1).join(' ');
  }

  return result;
}

function getLifecycleFlow() {
  const event = process.env.npm_lifecycle_event || '';
  if (!event.startsWith('task:')) return '';
  const inferred = event.replace('task:', '');
  return SUPPORTED_FLOWS.includes(inferred) ? inferred : '';
}

function clampAgents(value) {
  if (!Number.isFinite(value)) return 0;
  return Math.min(100, Math.max(1, value));
}

function parseAgentsValue(value) {
  if (!/^\d+$/.test(String(value))) return 0;
  return clampAgents(parseInt(value, 10));
}

function buildParseError(code, flag, value = '') {
  if (code === 'flag_invalido') {
    return {
      code,
      flag,
      value,
      message: `valor inválido para ${flag}: '${value}'.`,
    };
  }
  return {
    code,
    flag,
    value,
    message: `falta valor para ${flag}.`,
  };
}

function emitParseError(parsedArgs) {
  const payload = {
    error: parsedArgs.error.code,
    message: parsedArgs.error.message,
    flag: parsedArgs.error.flag,
    ...(parsedArgs.error.value ? { value: parsedArgs.error.value } : {}),
  };

  if (parsedArgs.wantsJson) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return;
  }

  process.stderr.write(`model task runner failed: ${parsedArgs.error.message}\n`);
  printUsage();
}
