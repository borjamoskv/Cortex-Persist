#!/usr/bin/env node

const { spawnSync } = await import('node:child_process');
const path = await import('node:path');
const fs = await import('node:fs');
const {
  maybeWriteAutomationLedger,
  resolveAutomationRunId,
  resolveLedgerConfig,
} = await import('./model-automation-ledger.mjs');

const dispatchStartedAt = Date.now();
const runId = resolveAutomationRunId(process.env);
const argv = process.argv.slice(2);
const separator = argv.indexOf('--');
const controlArgs = separator === -1 ? argv : argv.slice(0, separator);
const commandArgsInput = separator === -1 ? [] : argv.slice(separator + 1);

const usage = printUsage();
const wantsJson = controlArgs.includes('--json');
const enableAutoFlow = controlArgs.includes('--auto');
const wantsDryRun = controlArgs.includes('--dry-run');
const parsedControls = parseControlArgs(controlArgs);
if (parsedControls.error) {
  emitControlArgError(parsedControls.error, wantsJson, usage);
  process.exit(1);
}
const taskArgs = parsedControls.taskArgs;
let flow = parsedControls.flow;
const swarmAgents = parsedControls.swarmAgents;

const AUTOMATION_FLOWS = {
  build: {
    command: 'npm run build',
    description: 'Compila la web de Cortex-Persist',
  },
  release: {
    command: 'npm run build && node -e "console.log(\'release candidate listo\')"',
    description: 'Pipeline mínimo de build para release',
  },
  ship: {
    command: 'npm run build && node -e "console.log(\'artefacto preparado\')"',
    description: 'Ruta de preparación técnica base para shipping',
  },
  web: {
    command: 'npm run build',
    description: 'Compilación web estándar',
  },
  test: {
    command: 'npm run build',
    description: 'Chequeo de compilación para validación rápida',
  },
  swarm: {
    command: 'node scripts/model-swarm.mjs',
    description: 'Orquesta una ejecución multi-agente y usa consenso para el modelo sugerido.',
  },
  perfect: {
    command: 'node scripts/perfect-engine.mjs',
    description: 'Orquesta salud del repo, tests del router, build y ship gate rápido',
  },
};

const SUPPORTED_FLOWS = Object.keys(AUTOMATION_FLOWS);

if (controlArgs.includes('--help') || controlArgs.includes('-h') || controlArgs.length === 0) {
  process.stdout.write(usage);
  process.exit(0);
}

if (!flow) {
  flow = process.env.TASK_FLOW || process.env.CODEX_FLOW || process.env.MODEL_ROUTER_FLOW;
}

if (flow && !SUPPORTED_FLOWS.includes(flow)) {
  const error = {
    error: 'flujo_desconocido',
    message: `flujo inválido '${flow}'. Use uno de: ${SUPPORTED_FLOWS.join(', ')}`,
    requestedFlow: flow,
    supportedFlows: SUPPORTED_FLOWS,
  };
  if (wantsJson) {
    process.stdout.write(JSON.stringify(error, null, 2));
    process.stdout.write('\n');
  } else {
    process.stderr.write(`model dispatch failed: flujo inválido '${flow}'. Use uno de: ${SUPPORTED_FLOWS.join(', ')}\n`);
  }
  process.exit(1);
}

let commandArgs = [...commandArgsInput];

let taskText = taskArgs.join(' ').trim();
if (!taskText) {
  try {
    taskText = fs.readFileSync(0, 'utf8').toString().trim();
  } catch {
    taskText = '';
  }
}
taskText = normalizeTaskText(taskText);

const taskError = getTaskValidationError(taskText);
if (taskError) {
  const error = {
    error: taskError.code,
    message: taskError.message,
    usage: 'npm run model:dispatch -- "texto de tarea" -- "npm run build"',
  };
  if (wantsJson) {
    process.stdout.write(JSON.stringify(error, null, 2));
    process.stdout.write('\n');
  } else {
    process.stdout.write(usage);
  }
  process.exit(1);
}

if (!flow && enableAutoFlow) {
  flow = inferFlowFromTask(taskText);
}

if (!flow && enableAutoFlow) {
  process.stderr.write('model dispatch failed: --auto fue pedido, pero no se encontró flujo (TASK_FLOW o --flow=build|release|ship|web|test|swarm|perfect)\n');
  process.exit(1);
}

const routerPath = path.resolve(process.cwd(), 'scripts/model-router.mjs');
const routerStartedAt = Date.now();
const picker = spawnSync(process.execPath, [routerPath, '--json', taskText], {
  encoding: 'utf8',
  stdio: ['ignore', 'pipe', 'pipe'],
});
const routerDurationMs = Date.now() - routerStartedAt;

if (picker.error) {
  process.stderr.write(`model dispatch failed: cannot execute router (${picker.error.message})\n`);
  process.exit(1);
}

if (picker.status !== 0 || !picker.stdout.trim()) {
  process.stderr.write(`model dispatch failed: router returned status ${picker.status || 0}\n`);
  if (picker.stderr?.trim()) process.stderr.write(picker.stderr);
  process.exit(picker.status || 1);
}

let decision;
try {
  decision = JSON.parse(picker.stdout);
} catch (error) {
  process.stderr.write(`model dispatch failed: invalid router payload (${error.message})\n`);
  process.exit(1);
}

const envCommand = (
  process.env.TASK_COMMAND
  || process.env.CODEX_TASK_COMMAND
  || process.env.MODEL_ROUTER_COMMAND
  || ''
).trim();
let commandSource = '';
if (!commandArgs.length && envCommand) {
  commandArgs = [envCommand];
  commandSource = 'env';
}

if (flow && !commandArgs.length) {
  const selectedFlow = AUTOMATION_FLOWS[flow];
  if (!selectedFlow) {
    process.stderr.write(`model dispatch failed: flujo desconocido '${flow}'. Flujos disponibles: ${Object.keys(AUTOMATION_FLOWS).join(', ')}\n`);
    process.exit(1);
  }
  const flowCommand = flow === 'swarm' && swarmAgents
    ? `${selectedFlow.command} --agents=${swarmAgents}`
    : selectedFlow.command;
  commandArgs = [flowCommand];
  commandSource = 'flow';
}

if (commandArgs.length && !commandSource) {
  commandSource = 'cli';
}

if (!commandArgs.length) {
  const payload = {
    ...decision,
    ...(flow ? { flow } : {}),
    taskMetrics: buildTaskMetrics(taskText),
    timing: {
      totalMs: Date.now() - dispatchStartedAt,
      routerMs: routerDurationMs,
    },
  };
  const finalPayload = finalizeDispatcherPayload(payload, taskText);
  if (wantsJson) {
    process.stdout.write(JSON.stringify(finalPayload, null, 2));
    process.stdout.write('\n');
    process.exit(0);
  }
  process.stdout.write(`Recomendado: ${decision.recommended.id} (${Math.round(decision.recommended.confidence)}%)\n`);
  process.stdout.write(`Motivo: ${decision.recommended.reason}\n`);
  if (flow) {
    const selectedFlow = AUTOMATION_FLOWS[flow];
    process.stdout.write(`Flujo automático activo (${flow}): ${selectedFlow.description}\n`);
  }
  process.stdout.write(`Siguientes: ${decision.alternatives.map((entry) => `${entry.id} ${Math.round(entry.confidence)}%`).join(' | ')}\n`);
  process.exit(0);
}

const command = commandArgs.join(' ');

if (wantsDryRun) {
  const payload = {
    ...decision,
    flow,
    command,
    commandSource,
    swarmAgents: flow === 'swarm' && swarmAgents ? swarmAgents : undefined,
    taskMetrics: buildTaskMetrics(taskText),
    timing: {
      totalMs: Date.now() - dispatchStartedAt,
      routerMs: routerDurationMs,
    },
    dryRun: true,
    status: 'dry-run',
  };
  const finalPayload = finalizeDispatcherPayload(payload, taskText);
  if (wantsJson) {
    process.stdout.write(JSON.stringify(finalPayload, null, 2));
    process.stdout.write('\n');
  } else {
    process.stdout.write(`Flujo: ${flow}\n`);
    process.stdout.write(`Comando: ${command}\n`);
    process.stdout.write(`Modelo sugerido: ${decision.recommended.id} (${Math.round(decision.recommended.confidence)}%)\n`);
    process.stdout.write('Modo simulación (sin ejecutar).\n');
  }
  process.exit(0);
}

const modelEnv = {
  ...process.env,
  MODEL_AUTOMATION_RUN_ID: runId,
  CODEX_MODEL: decision.recommended.id,
  MODEL_DISPATCH: decision.recommended.id,
  MODEL_ROUTER_SELECTION: decision.recommended.id,
  MODEL_SWARM_TASK_TEXT: taskText,
  MODEL_SWARM_AGENTS: flow === 'swarm' && swarmAgents ? String(swarmAgents) : process.env.MODEL_SWARM_AGENTS,
  MODEL_AUTOMATION_LEDGER_SKIP: shouldSuppressChildLedger() ? '1' : process.env.MODEL_AUTOMATION_LEDGER_SKIP,
  MODEL_TASK_TEXT: taskText,
  TASK_TEXT: taskText,
};

if (wantsJson) {
  process.stderr.write(`Ejecutando con modelo ${decision.recommended.id}\n`);
} else {
  process.stdout.write(`Ejecutando con modelo ${decision.recommended.id}\n`);
}
const executionStartedAt = Date.now();
const run = spawnSync(command, wantsJson ? {
  shell: true,
  encoding: 'utf8',
  stdio: ['ignore', 'pipe', 'pipe'],
  env: modelEnv,
} : {
  shell: true,
  stdio: 'inherit',
  env: modelEnv,
});
const executionDurationMs = Date.now() - executionStartedAt;
const commandOutput = wantsJson ? buildCommandOutput(run.stdout, run.stderr) : {};

if (run.error) {
  const payload = {
    ...decision,
    executed: command,
    flow,
    commandSource,
    swarmAgents: flow === 'swarm' && swarmAgents ? swarmAgents : undefined,
    taskMetrics: buildTaskMetrics(taskText),
    timing: {
      totalMs: Date.now() - dispatchStartedAt,
      routerMs: routerDurationMs,
      executionMs: executionDurationMs,
    },
    ...commandOutput,
    status: 'failed',
    reason: run.error.message,
  };
  const finalPayload = finalizeDispatcherPayload(payload, taskText);
  if (wantsJson) {
    process.stdout.write(JSON.stringify(finalPayload, null, 2));
    process.stdout.write('\n');
  } else {
    process.stderr.write(`model dispatch failed while executing command: ${run.error.message}\n`);
  }
  process.exit(1);
}

if (run.status && run.status !== 0) {
  const payload = {
    ...decision,
    executed: command,
    flow,
    commandSource,
    swarmAgents: flow === 'swarm' && swarmAgents ? swarmAgents : undefined,
    taskMetrics: buildTaskMetrics(taskText),
    timing: {
      totalMs: Date.now() - dispatchStartedAt,
      routerMs: routerDurationMs,
      executionMs: executionDurationMs,
    },
    ...commandOutput,
    status: 'failed',
    exitCode: run.status,
  };
  const finalPayload = finalizeDispatcherPayload(payload, taskText);
  if (wantsJson) {
    process.stdout.write(JSON.stringify(finalPayload, null, 2));
    process.stdout.write('\n');
  } else {
    process.stderr.write(`model dispatch command finished with status ${run.status}\n`);
  }
  process.exit(run.status);
}

const payload = {
  ...decision,
  executed: command,
  flow,
  commandSource,
  swarmAgents: flow === 'swarm' && swarmAgents ? swarmAgents : undefined,
  taskMetrics: buildTaskMetrics(taskText),
  timing: {
    totalMs: Date.now() - dispatchStartedAt,
    routerMs: routerDurationMs,
    executionMs: executionDurationMs,
  },
  ...commandOutput,
  status: 'ok',
};
const finalPayload = finalizeDispatcherPayload(payload, taskText);
if (wantsJson) {
  process.stdout.write(JSON.stringify(finalPayload, null, 2));
  process.stdout.write('\n');
}

function printUsage() {
  return `Uso:
  npm run model:dispatch -- "texto de tarea"
  npm run model:dispatch -- "texto de tarea" -- "npm run build"
  npm run model:dispatch -- --json "texto de tarea" -- "npm run model:pick \"texto\""
  npm run model:dispatch -- --dry-run --auto --flow=web "texto de tarea"

Salida:
  - Sin comando: sugiere modelo (formato texto o JSON).
  - Con comando: ejecuta con la variable de entorno:
      CODEX_MODEL, MODEL_DISPATCH, MODEL_ROUTER_SELECTION
  - Con --dry-run: no ejecuta, solo muestra la resolución de comando y el modelo sugerido.
  - Alternativamente, define TASK_COMMAND (o CODEX_TASK_COMMAND / MODEL_ROUTER_COMMAND) para auto-ejecutar
    el comando sin pasar -- explícito.
  - Alternativamente, define TASK_FLOW (o CODEX_FLOW / MODEL_ROUTER_FLOW) para seleccionar un flujo predefinido.
  - Para el flujo swarm puedes usar --agents=<n> para fijar el tamaño del consenso.
  - Usa --auto --flow=<build|release|ship|web|test|swarm|perfect> para seleccionar un comando automático.
  - Si usas --auto sin flow, el dispatcher intenta inferir el flujo por contexto del texto.
\n`;
}

function isControlArg(arg) {
  return (
    arg === '--json'
    || arg === '--auto'
    || arg === '--help'
    || arg === '--dry-run'
    || arg === '-h'
    || arg === '--flow'
    || arg === '--agents'
    || arg.startsWith('--flow=')
    || arg.startsWith('--agents=')
  );
}

function parseControlArgs(args) {
  const result = {
    flow: '',
    swarmAgents: 0,
    taskArgs: [],
    error: null,
  };

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];

    if (arg === '--flow') {
      const next = args[i + 1];
      if (!next || isControlArg(next)) {
        result.error = buildControlArgError('flag_incompleto', '--flow', next);
        return result;
      }
      result.flow = next;
      i += 1;
      continue;
    }

    if (arg === '--agents') {
      const next = args[i + 1];
      if (!next || isControlArg(next)) {
        result.error = buildControlArgError('flag_incompleto', '--agents', next);
        return result;
      }
      const parsedAgents = parseAgentsValue(next);
      if (!parsedAgents) {
        result.error = buildControlArgError('flag_invalido', '--agents', next);
        return result;
      }
      result.swarmAgents = parsedAgents;
      i += 1;
      continue;
    }

    if (arg.startsWith('--flow=')) {
      const value = arg.slice('--flow='.length).trim();
      if (!value) {
        result.error = buildControlArgError('flag_incompleto', '--flow');
        return result;
      }
      result.flow = value;
      continue;
    }

    if (arg.startsWith('--agents=')) {
      const value = arg.slice('--agents='.length).trim();
      const parsedAgents = parseAgentsValue(value);
      if (!parsedAgents) {
        result.error = buildControlArgError('flag_invalido', '--agents', value);
        return result;
      }
      result.swarmAgents = parsedAgents;
      continue;
    }

    if (isControlArg(arg)) {
      continue;
    }

    result.taskArgs.push(arg);
  }

  return result;
}

function buildControlArgError(code, flag, value = '') {
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

function emitControlArgError(error, wantsJsonOutput, usageText) {
  const payload = {
    error: error.code,
    message: error.message,
    flag: error.flag,
    ...(error.value ? { value: error.value } : {}),
  };

  if (wantsJsonOutput) {
    process.stdout.write(JSON.stringify(payload, null, 2));
    process.stdout.write('\n');
    return;
  }

  process.stderr.write(`model dispatch failed: ${error.message}\n`);
  process.stdout.write(usageText);
}

function inferFlowFromTask(taskText) {
  const normalized = taskText.toLowerCase();
  const has = (keyword) => normalized.includes(keyword);

  if (has('perfect') || has('perfecto') || has('perfecta') || has('perfeccion') || has('perfección') || has('blindar') || has('harden') || has('hardening')) {
    return 'perfect';
  }
  if (has('release') || has('publica') || has('deploy') || has('despliegue') || has('shipping') || has('ship')) {
    return 'release';
  }
  if (has('test') || has('prueba') || has('verificar') || has('validar') || has('qa')) {
    return 'test';
  }
  if (has('artifact') || has('artefacto') || has('prepare') || has('prepara') || has('ship')) {
    return 'ship';
  }
  if (has('web') || has('sitio') || has('landing') || has('pagina') || has('página')) {
    return 'web';
  }
  return 'build';
}

function clampAgents(value) {
  if (!Number.isFinite(value)) return 0;
  return Math.min(100, Math.max(1, value));
}

function parseAgentsValue(value) {
  if (!/^\d+$/.test(String(value))) return 0;
  return clampAgents(parseInt(value, 10));
}

function normalizeTaskText(value) {
  return value.replace(/\s+/g, ' ').trim();
}

function getTaskValidationError(taskText) {
  if (!taskText) {
    return {
      code: 'tarea_vacia',
      message: 'texto de tarea vacío. Pasa un texto como argumento o por stdin.',
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

function buildTaskMetrics(taskText) {
  return {
    characters: taskText.length,
    words: taskText ? taskText.split(/\s+/).filter(Boolean).length : 0,
  };
}

function buildCommandOutput(stdout, stderr) {
  const payload = {};
  const normalizedStdout = (stdout || '').trim();
  const normalizedStderr = (stderr || '').trim();

  if (normalizedStdout) {
    const parsed = tryParseJsonPayload(normalizedStdout);
    if (parsed !== undefined) {
      const serialized = JSON.stringify(parsed);
      if (serialized.length > getCommandOutputLimit()) {
        payload.commandResult = summarizeParsedCommandResult(parsed);
        payload.commandResultTruncated = true;
        payload.commandResultOriginalChars = serialized.length;
      } else {
        payload.commandResult = parsed;
      }
    } else {
      Object.assign(payload, buildTextOutputFields('commandStdout', normalizedStdout));
    }
  }

  if (normalizedStderr) {
    Object.assign(payload, buildTextOutputFields('commandStderr', normalizedStderr));
  }

  return payload;
}

function buildTextOutputFields(fieldName, value) {
  const limit = getCommandOutputLimit();
  if (value.length <= limit) {
    return { [fieldName]: value };
  }

  return {
    [fieldName]: value.slice(0, limit),
    [`${fieldName}Truncated`]: true,
    [`${fieldName}OriginalChars`]: value.length,
  };
}

function summarizeParsedCommandResult(result) {
  if (!result || typeof result !== 'object' || Array.isArray(result)) {
    return result;
  }

  const summary = {};
  const keys = [
    'engine',
    'status',
    'flow',
    'agents',
    'consensus',
    'consensusRatio',
    'averageConfidence',
    'recommended',
    'alternatives',
    'taskMetrics',
    'timing',
    'shouldExecute',
    'guardedReason',
    'exitCode',
    'reason',
  ];

  for (const key of keys) {
    if (key in result) {
      summary[key] = result[key];
    }
  }

  return Object.keys(summary).length
    ? summary
    : { preview: JSON.stringify(result).slice(0, getCommandOutputLimit()) };
}

function getCommandOutputLimit() {
  return parseInt(process.env.MODEL_COMMAND_OUTPUT_LIMIT_CHARS || '4000', 10);
}

function finalizeDispatcherPayload(payload, taskText) {
  const payloadWithRunId = {
    runId,
    ...payload,
  };
  const ledger = persistDispatcherLedger(payload, taskText);
  if (ledger.enabled) {
    return {
      ...payloadWithRunId,
      ledger,
    };
  }
  return payloadWithRunId;
}

function persistDispatcherLedger(payload, taskText) {
  const entry = stripUndefined({
    runId,
    source: 'model-dispatcher',
    engine: 'dispatch',
    status: payload.status || 'recommended',
    flow: payload.flow,
    commandSource: payload.commandSource,
    model: payload.recommended?.id,
    confidence: payload.recommended?.confidence,
    swarmAgents: payload.swarmAgents,
    taskPreview: buildTaskPreview(taskText),
    taskMetrics: payload.taskMetrics,
    timing: payload.timing,
    executed: payload.executed,
    exitCode: payload.exitCode,
    reason: payload.reason,
    guardedReason: payload.guardedReason,
    consensus: payload.commandResult ? summarizeParsedCommandResult(payload.commandResult).consensus : undefined,
    consensusRatio: payload.commandResult ? summarizeParsedCommandResult(payload.commandResult).consensusRatio : undefined,
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

function shouldSuppressChildLedger() {
  const config = resolveLedgerConfig(process.env, process.cwd());
  if (!config.enabled) {
    return false;
  }
  const allowChild = String(process.env.MODEL_AUTOMATION_LEDGER_ALLOW_CHILD || '').trim().toLowerCase();
  return allowChild !== '1' && allowChild !== 'true';
}

function tryParseJsonPayload(value) {
  const candidates = [value];
  const objectStart = value.lastIndexOf('\n{');
  const arrayStart = value.lastIndexOf('\n[');

  if (objectStart !== -1) {
    candidates.push(value.slice(objectStart + 1).trim());
  }
  if (arrayStart !== -1) {
    candidates.push(value.slice(arrayStart + 1).trim());
  }

  for (const candidate of candidates) {
    try {
      return JSON.parse(candidate);
    } catch {
      continue;
    }
  }

  return undefined;
}
