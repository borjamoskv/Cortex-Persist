#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const nodePath = process.execPath;
const scriptsRoot = path.resolve(process.cwd(), 'scripts');

const tests = [
  testInvalidFlowJson,
  testDispatchFailedCommandJson,
  testBlankTaskWithJson,
  testWhitespaceTaskCommandIgnored,
  testDispatcherRejectsIncompleteFlagValue,
  testDispatcherRejectsInvalidFlowBeforeTaskValidation,
  testPerfectEngineDryRunJson,
  testPerfectEngineExecutesWithOverrides,
  testAutoFlowFromStdin,
  testTaskRunnerReadsStdin,
  testTaskRunnerDryRunPassthrough,
  testTaskRunnerRejectsIncompleteAgentsFlag,
  testTaskRunnerSwarmAgentsPassthroughDryRun,
  testTaskRunnerSwarmSupportsExactHundredAgents,
  testTaskRunnerFlagsOrder,
  testTaskRunnerInvalidFlow,
  testTaskRunnerLifecycleFlowAuto,
  testSwarmDefaultAgentCount,
  testSwarmCustomAgentCount,
  testSwarmSupportsExactHundredAgents,
  testSwarmExecutionUsesModelEnv,
  testDispatcherSwarmAgentsDryRun,
  testDispatcherSwarmSupportsExactHundredAgents,
  testDispatcherJsonExecutionIsPureJson,
  testTaskRunnerSwarmLifecyclePassesTaskText,
  testSwarmTaskTextFromEnvFallback,
  testDispatcherSplitAgentsArgDoesNotPolluteTask,
  testDispatcherJsonIncludesMetrics,
  testTaskRunnerSwarmJsonIsPureAndEmbedsChildResult,
  testDispatcherTruncatesVerboseCommandStdout,
  testDispatcherSummarizesLargeChildJson,
  testDispatcherWritesLedgerWhenEnabled,
  testTaskRunnerSwarmWritesSingleLedgerEntry,
  testDispatcherLedgerRotatesBySize,
  testDispatcherHonorsProvidedRunId,
  testTaskRunnerSwarmSharesRunIdWithChildResult,
  testLedgerReportJsonAggregatesEntries,
  testLedgerReportFiltersAndNoRotate,
  testLedgerReportHandlesEmptyLedger,
  testLedgerReportJsonErrorsRespectJsonFlag,
  testSwarmJsonIncludesMetrics,
  testSwarmGuardsRecursiveFlow,
  testFlowMappingsExecuted,
  testFlowMappingsDryRun,
  testRouterGuideText,
  testRouterGuideJson,
];

for (const test of tests) {
  try {
    test();
    // eslint-disable-next-line no-console
    console.log(`PASS: ${test.name}`);
  } catch (error) {
    console.error(`FAIL: ${test.name}`);
    console.error(error.message);
    process.exit(1);
  }
}

function runScript(relativeScript, args, env = {}, input = undefined) {
  return spawnSync(nodePath, [path.join(scriptsRoot, relativeScript), ...args], {
    encoding: 'utf8',
    cwd: process.cwd(),
    input,
    env: {
      ...process.env,
      ...env,
    },
    stdio: ['pipe', 'pipe', 'pipe'],
  });
}

function extractJsonFromEnd(stdout) {
  const start = stdout.lastIndexOf('\n{');
  const payload = start === -1 ? stdout.trim() : stdout.slice(start + 1).trim();
  return JSON.parse(payload);
}

function createLedgerHarness(extraEnv = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'model-ledger-'));
  const ledgerPath = path.join(dir, 'model-automation-ledger.jsonl');
  return {
    dir,
    ledgerPath,
    env: {
      MODEL_AUTOMATION_LEDGER_ENABLED: '1',
      MODEL_AUTOMATION_LEDGER_PATH: ledgerPath,
      MODEL_AUTOMATION_LEDGER_MAX_BYTES: '4096',
      ...extraEnv,
    },
  };
}

function readJsonLines(filePath) {
  return fs.readFileSync(filePath, 'utf8')
    .trim()
    .split('\n')
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function writeJsonLines(filePath, entries) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const payload = entries.map((entry) => JSON.stringify(entry)).join('\n');
  fs.writeFileSync(filePath, payload ? `${payload}\n` : '', 'utf8');
}

function testInvalidFlowJson() {
  const result = runScript('model-dispatcher.mjs', ['--json', '--flow=invalid', 'texto'], { TASK_COMMAND: '' });
  assert.equal(result.status, 1, 'esperaba salida en error para flujo inválido');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.error, 'flujo_desconocido');
  assert.equal(payload.requestedFlow, 'invalid');
}

function testDispatchFailedCommandJson() {
  const result = runScript('model-dispatcher.mjs', ['--auto', '--json', 'necesito lanzar tarea'], {
    TASK_FLOW: 'web',
    TASK_COMMAND: 'false',
  });
  assert.equal(result.status, 1, 'esperaba salida en error por comando fallido');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.status, 'failed');
  assert.equal(payload.exitCode, 1);
  assert.equal(payload.executed, 'false');
}

function testBlankTaskWithJson() {
  const result = runScript('model-dispatcher.mjs', ['--json'], {}, '');
  assert.equal(result.status, 1, 'esperaba error cuando no hay texto de tarea');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.error, 'tarea_vacia');
}

function testWhitespaceTaskCommandIgnored() {
  const result = runScript('model-dispatcher.mjs', ['--json', 'texto breve'], {
    TASK_COMMAND: '   ',
  });
  assert.equal(result.status, 0, 'esperaba solo recomendación sin ejecución de comando');
  const payload = extractJsonFromEnd(result.stdout);
  assert.ok(!('executed' in payload), 'no debería ejecutar comando con TASK_COMMAND en blanco');
}

function testDispatcherRejectsIncompleteFlagValue() {
  const result = runScript('model-dispatcher.mjs', ['--json', '--flow', '--agents=7', 'texto']);
  assert.equal(result.status, 1, 'esperaba error explícito para flag incompleto');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.error, 'flag_incompleto');
  assert.equal(payload.flag, '--flow');
}

function testDispatcherRejectsInvalidFlowBeforeTaskValidation() {
  const result = runScript('model-dispatcher.mjs', ['--json', '--flow', 'texto de tarea']);
  assert.equal(result.status, 1, 'esperaba error por flujo inválido aunque no quede tarea separada');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.error, 'flujo_desconocido');
  assert.equal(payload.requestedFlow, 'texto de tarea');
}

function testPerfectEngineDryRunJson() {
  const result = runScript('perfect-engine.mjs', ['--dry-run', '--json']);
  assert.equal(result.status, 0, 'esperaba dry-run válido del motor perfect');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.engine, 'perfect');
  assert.equal(payload.dryRun, true);
  assert.equal(payload.steps.length, 4);
  assert.ok(payload.steps.some((step) => step.id === 'ship-gate'), 'debería incluir ship-gate');
}

function testPerfectEngineExecutesWithOverrides() {
  const ok = 'node -e "process.exit(0)"';
  const result = runScript('perfect-engine.mjs', ['--json'], {
    CORTEX_PERFECT_REPO_HEALTH_CMD: ok,
    CORTEX_PERFECT_MODEL_TESTS_CMD: ok,
    CORTEX_PERFECT_BUILD_CMD: ok,
    CORTEX_PERFECT_SHIP_GATE_CMD: ok,
  });
  assert.equal(result.status, 0, 'esperaba ejecución exitosa con overrides triviales');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.status, 'ok');
  assert.ok(payload.steps.every((step) => step.status === 'ok'), 'todos los pasos deberían pasar');
}

function testAutoFlowFromStdin() {
  const result = runScript(
    'model-task-runner.mjs',
    ['--json'],
    {
      TASK_COMMAND: 'node -e "console.log(process.env.CODEX_MODEL)"',
    },
    'texto desde stdin sin flow',
  );
  assert.equal(result.status, 0, 'esperaba inferencia automática de flujo cuando no se provee explícito');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.status, 'ok');
  assert.equal(payload.executed, 'node -e "console.log(process.env.CODEX_MODEL)"');
}

function testTaskRunnerReadsStdin() {
  const result = runScript(
    'model-task-runner.mjs',
    ['build', '--json'],
    {
      TASK_COMMAND: 'node -e "console.log(process.env.CODEX_MODEL)"',
      MODEL_TEST_MARKER: '1',
    },
    'texto proveniente de stdin',
  );
  assert.equal(result.status, 0, 'esperaba ejecución exitosa leyendo texto de stdin');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.status, 'ok');
  assert.equal(payload.executed, 'node -e "console.log(process.env.CODEX_MODEL)"');
}

function testTaskRunnerDryRunPassthrough() {
  const result = runScript(
    'model-task-runner.mjs',
    ['perfect', '--json', '--dry-run', 'texto de prueba'],
    {
      TASK_COMMAND: 'false',
    },
  );
  assert.equal(result.status, 0, 'esperaba que --dry-run evitara la ejecución real');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.flow, 'perfect');
  assert.equal(payload.status, 'dry-run');
  assert.equal(payload.command, 'false');
}

function testTaskRunnerRejectsIncompleteAgentsFlag() {
  const result = runScript(
    'model-task-runner.mjs',
    ['swarm', '--json', '--agents', '--dry-run', 'texto de prueba'],
  );
  assert.equal(result.status, 1, 'esperaba error explícito para --agents incompleto');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.error, 'flag_incompleto');
  assert.equal(payload.flag, '--agents');
}

function testTaskRunnerSwarmAgentsPassthroughDryRun() {
  const result = runScript(
    'model-task-runner.mjs',
    ['swarm', '--json', '--dry-run', '--agents=7', 'texto de prueba swarm'],
  );
  assert.equal(result.status, 0, 'esperaba dry-run correcto del swarm con agentes custom');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.flow, 'swarm');
  assert.equal(payload.status, 'dry-run');
  assert.equal(payload.swarmAgents, 7);
  assert.equal(payload.command, 'node scripts/model-swarm.mjs --agents=7');
}

function testTaskRunnerSwarmSupportsExactHundredAgents() {
  const result = runScript(
    'model-task-runner.mjs',
    ['swarm', '--json', '--dry-run', '--agents=100', 'texto de prueba swarm 100'],
  );
  assert.equal(result.status, 0, 'esperaba dry-run correcto del swarm con 100 agentes');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.flow, 'swarm');
  assert.equal(payload.swarmAgents, 100);
  assert.equal(payload.command, 'node scripts/model-swarm.mjs --agents=100');
}

function testTaskRunnerFlagsOrder() {
  const result = runScript(
    'model-task-runner.mjs',
    ['web', 'texto de flujo por posición', '--json'],
    {
      TASK_COMMAND: 'node -e "console.log(process.env.CODEX_MODEL)"',
    },
  );
  assert.equal(result.status, 0, 'esperaba ejecución exitosa con --json en posición final');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.status, 'ok');
  assert.equal(payload.executed, 'node -e "console.log(process.env.CODEX_MODEL)"');
}

function testTaskRunnerInvalidFlow() {
  const result = runScript(
    'model-task-runner.mjs',
    ['--json', '--flow=invalid', 'texto sin sentido'],
    {
      TASK_COMMAND: 'node -e "console.log(process.env.CODEX_MODEL)"',
    },
  );
  assert.equal(result.status, 1, 'esperaba error al pasar --flow inválido');
  assert.equal((result.stderr || '').includes("flujo desconocido 'invalid'"), true, 'esperaba mensaje de flujo desconocido');
}

function testTaskRunnerLifecycleFlowAuto() {
  const result = runScript(
    'model-task-runner.mjs',
    ['--json', 'texto desde flujo lifecycle'],
    {
      TASK_COMMAND: 'node -e "console.log(process.env.CODEX_MODEL)"',
      npm_lifecycle_event: 'task:release',
    },
  );
  assert.equal(result.status, 0, 'esperaba éxito usando flujo inferido por lifecycle event');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.status, 'ok');
  assert.equal(payload.flow, 'release');
  assert.equal(payload.executed, 'node -e "console.log(process.env.CODEX_MODEL)"');
}

function testSwarmDefaultAgentCount() {
  const result = runScript('model-swarm.mjs', ['--json', 'texto para consenso']);
  assert.equal(result.status, 0, 'esperaba salida OK del motor swarm por defecto');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.engine, 'swarm');
  assert.equal(payload.agents, 21, 'esperaba 21 agentes por defecto');
  assert.equal(payload.recommendations.length, 21, 'esperaba recomendación por agente');
}

function testSwarmCustomAgentCount() {
  const result = runScript('model-swarm.mjs', ['--json', '--agents=7', 'texto para consenso corto']);
  assert.equal(result.status, 0, 'esperaba salida OK del motor swarm con 7 agentes');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.agents, 7, 'esperaba respetar número custom de agentes');
}

function testSwarmSupportsExactHundredAgents() {
  const result = runScript('model-swarm.mjs', ['--json', '--agents=100', 'texto para consenso cien']);
  assert.equal(result.status, 0, 'esperaba salida OK del motor swarm con 100 agentes');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.agents, 100, 'esperaba respetar exactamente 100 agentes');
  assert.equal(payload.recommendations.length, 100);
}

function testSwarmExecutionUsesModelEnv() {
  const result = runScript(
    'model-swarm.mjs',
    ['--json', '--agents=11', 'texto de validación de ejecución'],
    {
      TASK_COMMAND: 'node -e "process.exit(process.env.CODEX_MODEL ? 0 : 1)"',
    },
  );
  assert.equal(result.status, 0, 'esperaba ejecución correcta del motor swarm');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.agents, 11, 'esperaba respetar 11 agentes');
  assert.equal(payload.status, 'ok', 'esperaba estado ok tras ejecutar comando');
  assert.equal(payload.shouldExecute, true, 'esperaba ejecución real al tener comando de tarea');
  assert.equal(payload.exitCode, undefined);
}

function testDispatcherSwarmAgentsDryRun() {
  const result = runScript(
    'model-dispatcher.mjs',
    ['--json', '--dry-run', '--flow=swarm', '--agents=9', 'texto de swarm'],
  );
  assert.equal(result.status, 0, 'esperaba dry-run correcto del dispatcher swarm');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.flow, 'swarm');
  assert.equal(payload.swarmAgents, 9);
  assert.equal(payload.command, 'node scripts/model-swarm.mjs --agents=9');
}

function testDispatcherSwarmSupportsExactHundredAgents() {
  const result = runScript(
    'model-dispatcher.mjs',
    ['--json', '--dry-run', '--flow=swarm', '--agents=100', 'texto de swarm cien'],
  );
  assert.equal(result.status, 0, 'esperaba dry-run correcto del dispatcher swarm con 100 agentes');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.flow, 'swarm');
  assert.equal(payload.swarmAgents, 100);
  assert.equal(payload.command, 'node scripts/model-swarm.mjs --agents=100');
}

function testDispatcherJsonExecutionIsPureJson() {
  const result = runScript(
    'model-dispatcher.mjs',
    ['--json', '--flow=build', 'texto con comando'],
    {
      TASK_COMMAND: 'node -e "process.exit(0)"',
    },
  );
  assert.equal(result.status, 0, 'esperaba ejecución JSON válida');
  assert.doesNotThrow(() => JSON.parse(result.stdout.trim()), 'stdout debería ser JSON puro');
  assert.equal((result.stderr || '').includes('Ejecutando con modelo'), true, 'el log operativo debería moverse a stderr');
}

function testTaskRunnerSwarmLifecyclePassesTaskText() {
  const taskText = 'texto de flujo limpio para swarm';
  const command = "node -e \"console.log('TASK_TEXT=' + process.env.MODEL_TASK_TEXT)\"";
  const result = runScript(
    'model-task-runner.mjs',
    ['--json', taskText],
    {
      TASK_COMMAND: command,
      npm_lifecycle_event: 'task:swarm',
    },
  );
  assert.equal(result.status, 0, 'esperaba éxito en ejecución del flow swarm desde lifecycle');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.flow, 'swarm', 'esperaba flow swarm');
  assert.equal(payload.status, 'ok', 'esperaba estado ok al ejecutar TASK_COMMAND');
  assert.equal(payload.executed, command, 'esperaba que se ejecutara el comando del entorno');
  assert.equal(payload.commandStdout, `TASK_TEXT=${taskText}`, 'el comando debería recibir exactamente el texto de tarea, sin el token de flujo');
}

function testSwarmTaskTextFromEnvFallback() {
  const result = runScript(
    'model-swarm.mjs',
    ['--json'],
    {
      MODEL_SWARM_TASK_TEXT: 'texto desde env fallback',
      MODEL_SWARM_AGENTS: '11',
    },
  );
  assert.equal(result.status, 0, 'esperaba salida ok con texto de tarea por env fallback');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.engine, 'swarm');
  assert.equal(payload.agents, 11);
}

function testDispatcherSplitAgentsArgDoesNotPolluteTask() {
  const result = runScript(
    'model-dispatcher.mjs',
    ['--json', '--dry-run', '--flow', 'swarm', '--agents', '9', 'texto limpio'],
  );
  assert.equal(result.status, 0, 'esperaba dry-run válido con --agents separado');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.flow, 'swarm');
  assert.equal(payload.swarmAgents, 9);
  assert.equal(payload.command, 'node scripts/model-swarm.mjs --agents=9');
  assert.equal(payload.taskMetrics.characters, 'texto limpio'.length);
}

function testDispatcherJsonIncludesMetrics() {
  const result = runScript(
    'model-dispatcher.mjs',
    ['--json', '--dry-run', '--flow=web', 'texto breve para métricas'],
  );
  assert.equal(result.status, 0, 'esperaba dry-run con métricas en dispatcher');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.status, 'dry-run');
  assert.equal(payload.commandSource, 'flow');
  assert.equal(payload.taskMetrics.words, 4);
  assert.equal(typeof payload.timing.totalMs, 'number');
  assert.equal(typeof payload.timing.routerMs, 'number');
}

function testTaskRunnerSwarmJsonIsPureAndEmbedsChildResult() {
  const result = runScript(
    'model-task-runner.mjs',
    ['swarm', '--json', '--agents=5', 'texto puro para swarm'],
  );
  assert.equal(result.status, 0, 'esperaba salida JSON pura en task runner swarm');
  assert.doesNotThrow(() => JSON.parse(result.stdout.trim()), 'stdout debería permanecer como JSON puro');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.flow, 'swarm');
  assert.equal(payload.swarmAgents, 5);
  assert.equal(payload.status, 'ok');
  assert.equal(payload.commandResult.engine, 'swarm');
  assert.equal(payload.commandResult.agents, 5);
}

function testDispatcherTruncatesVerboseCommandStdout() {
  const result = runScript(
    'model-dispatcher.mjs',
    ['--json', '--flow=build', 'texto con salida larga'],
    {
      TASK_COMMAND: 'node -e "process.stdout.write(\'x\'.repeat(80))"',
      MODEL_COMMAND_OUTPUT_LIMIT_CHARS: '32',
    },
  );
  assert.equal(result.status, 0, 'esperaba ejecución correcta con truncado de stdout');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.commandStdout.length, 32);
  assert.equal(payload.commandStdoutTruncated, true);
  assert.equal(payload.commandStdoutOriginalChars, 80);
}

function testDispatcherSummarizesLargeChildJson() {
  const result = runScript(
    'model-dispatcher.mjs',
    ['--json', '--flow=build', 'texto con hijo json grande'],
    {
      TASK_COMMAND: 'node -e "process.stdout.write(JSON.stringify({engine:\'swarm\',status:\'planned\',agents:21,consensus:{model:\'gpt-5.3-codex\',count:21},recommendations:new Array(50).fill({agent:1,model:\'gpt-5.3-codex\'})}))"',
      MODEL_COMMAND_OUTPUT_LIMIT_CHARS: '120',
    },
  );
  assert.equal(result.status, 0, 'esperaba ejecución correcta con resumen de JSON grande');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.commandResult.engine, 'swarm');
  assert.equal(payload.commandResult.agents, 21);
  assert.equal(payload.commandResultTruncated, true);
  assert.equal(typeof payload.commandResultOriginalChars, 'number');
  assert.equal(payload.commandResult.recommendations, undefined);
}

function testDispatcherWritesLedgerWhenEnabled() {
  const harness = createLedgerHarness();
  try {
    const result = runScript(
      'model-dispatcher.mjs',
      ['--json', '--dry-run', '--flow=web', 'texto con ledger'],
      harness.env,
    );
    assert.equal(result.status, 0, 'esperaba dry-run válido con ledger habilitado');
    const payload = JSON.parse(result.stdout.trim());
    assert.equal(payload.ledger.written, true);
    assert.equal(payload.ledger.path, harness.ledgerPath);

    const entries = readJsonLines(harness.ledgerPath);
    assert.equal(entries.length, 1);
    assert.equal(entries[0].source, 'model-dispatcher');
    assert.equal(entries[0].engine, 'dispatch');
    assert.equal(entries[0].status, 'dry-run');
    assert.equal(entries[0].flow, 'web');
  } finally {
    fs.rmSync(harness.dir, { recursive: true, force: true });
  }
}

function testTaskRunnerSwarmWritesSingleLedgerEntry() {
  const harness = createLedgerHarness();
  try {
    const result = runScript(
      'model-task-runner.mjs',
      ['swarm', '--json', '--agents=5', 'texto con ledger swarm'],
      harness.env,
    );
    assert.equal(result.status, 0, 'esperaba ejecución válida de task runner swarm con ledger');
    const payload = JSON.parse(result.stdout.trim());
    assert.equal(payload.ledger.written, true);

    const entries = readJsonLines(harness.ledgerPath);
    assert.equal(entries.length, 1, 'el wrapper debe registrar una sola entrada y suprimir el hijo');
    assert.equal(entries[0].source, 'model-dispatcher');
    assert.equal(entries[0].flow, 'swarm');
    assert.equal(entries[0].swarmAgents, 5);
  } finally {
    fs.rmSync(harness.dir, { recursive: true, force: true });
  }
}

function testDispatcherLedgerRotatesBySize() {
  const harness = createLedgerHarness({ MODEL_AUTOMATION_LEDGER_MAX_BYTES: '250' });
  try {
    const first = runScript(
      'model-dispatcher.mjs',
      ['--json', '--dry-run', '--flow=web', 'texto uno para rotacion'],
      harness.env,
    );
    assert.equal(first.status, 0);

    const second = runScript(
      'model-dispatcher.mjs',
      ['--json', '--dry-run', '--flow=web', 'texto dos para rotacion con algo mas de volumen'],
      harness.env,
    );
    assert.equal(second.status, 0);
    const payload = JSON.parse(second.stdout.trim());
    assert.equal(payload.ledger.rotated, true);
    assert.equal(fs.existsSync(`${harness.ledgerPath}.1`), true, 'debería existir el backup rotado');
  } finally {
    fs.rmSync(harness.dir, { recursive: true, force: true });
  }
}

function testDispatcherHonorsProvidedRunId() {
  const harness = createLedgerHarness({ MODEL_AUTOMATION_RUN_ID: 'run-fixed-123' });
  try {
    const result = runScript(
      'model-dispatcher.mjs',
      ['--json', '--dry-run', '--flow=web', 'texto con run id fijo'],
      harness.env,
    );
    assert.equal(result.status, 0);
    const payload = JSON.parse(result.stdout.trim());
    assert.equal(payload.runId, 'run-fixed-123');

    const entries = readJsonLines(harness.ledgerPath);
    assert.equal(entries.length, 1);
    assert.equal(entries[0].runId, 'run-fixed-123');
  } finally {
    fs.rmSync(harness.dir, { recursive: true, force: true });
  }
}

function testTaskRunnerSwarmSharesRunIdWithChildResult() {
  const result = runScript(
    'model-task-runner.mjs',
    ['swarm', '--json', '--agents=5', 'texto con run id compartido'],
    {
      MODEL_AUTOMATION_RUN_ID: 'run-shared-456',
    },
  );
  assert.equal(result.status, 0);
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.runId, 'run-shared-456');
  assert.equal(payload.commandResult.runId, 'run-shared-456');
}

function testLedgerReportJsonAggregatesEntries() {
  const harness = createLedgerHarness();
  try {
    writeJsonLines(`${harness.ledgerPath}.1`, [
      {
        timestamp: '2026-04-14T08:59:00.000Z',
        runId: 'run-older',
        source: 'model-dispatcher',
        engine: 'dispatch',
        status: 'failed',
        flow: 'build',
        model: 'gpt-5.3-codex',
        timing: { totalMs: 15, routerMs: 5, executionMs: 7 },
      },
    ]);
    writeJsonLines(harness.ledgerPath, [
      {
        timestamp: '2026-04-14T09:00:00.000Z',
        runId: 'run-web',
        source: 'model-dispatcher',
        engine: 'dispatch',
        status: 'dry-run',
        flow: 'web',
        model: 'gpt-5.4',
        timing: { totalMs: 10, routerMs: 4 },
      },
      {
        timestamp: '2026-04-14T09:01:00.000Z',
        runId: 'run-swarm',
        source: 'model-swarm',
        engine: 'swarm',
        status: 'ok',
        flow: 'swarm',
        model: 'gpt-5.3-codex',
        timing: { totalMs: 20, routerTotalMs: 12, executionMs: 6 },
      },
    ]);

    const result = runScript(
      'model-automation-report.mjs',
      ['--json', '--path', harness.ledgerPath],
    );
    assert.equal(result.status, 0, 'esperaba reporte JSON correcto del ledger');
    const payload = JSON.parse(result.stdout.trim());
    assert.equal(payload.status, 'ok');
    assert.equal(payload.totals.entries, 3);
    assert.equal(payload.totals.runs, 3);
    assert.equal(payload.totals.completedEntries, 2);
    assert.equal(payload.totals.successRate, 0.5);
    assert.equal(payload.byFlow.find((entry) => entry.flow === 'swarm').count, 1);
    assert.equal(payload.byModel.find((entry) => entry.model === 'gpt-5.3-codex').count, 2);
    assert.equal(payload.runs[0].runId, 'run-swarm');
    assert.equal(payload.files.length, 2);
  } finally {
    fs.rmSync(harness.dir, { recursive: true, force: true });
  }
}

function testLedgerReportFiltersAndNoRotate() {
  const harness = createLedgerHarness();
  try {
    writeJsonLines(`${harness.ledgerPath}.1`, [
      {
        timestamp: '2026-04-14T08:59:00.000Z',
        runId: 'run-older',
        source: 'model-dispatcher',
        engine: 'dispatch',
        status: 'failed',
        flow: 'build',
        model: 'gpt-5.3-codex',
      },
    ]);
    writeJsonLines(harness.ledgerPath, [
      {
        timestamp: '2026-04-14T09:01:00.000Z',
        runId: 'run-swarm',
        source: 'model-swarm',
        engine: 'swarm',
        status: 'ok',
        flow: 'swarm',
        model: 'gpt-5.3-codex',
      },
    ]);

    const filtered = runScript(
      'model-automation-report.mjs',
      ['--json', '--path', harness.ledgerPath, '--flow=swarm', '--model=gpt-5.3-codex'],
    );
    assert.equal(filtered.status, 0);
    const filteredPayload = JSON.parse(filtered.stdout.trim());
    assert.equal(filteredPayload.totals.entries, 1);
    assert.equal(filteredPayload.runs.length, 1);
    assert.equal(filteredPayload.runs[0].runId, 'run-swarm');

    const noRotate = runScript(
      'model-automation-report.mjs',
      ['--json', '--path', harness.ledgerPath, '--run-id=run-older', '--no-rotate'],
    );
    assert.equal(noRotate.status, 0);
    const noRotatePayload = JSON.parse(noRotate.stdout.trim());
    assert.equal(noRotatePayload.status, 'empty');
    assert.equal(noRotatePayload.totals.entries, 0);
    assert.equal(noRotatePayload.files.length, 1);
  } finally {
    fs.rmSync(harness.dir, { recursive: true, force: true });
  }
}

function testLedgerReportHandlesEmptyLedger() {
  const harness = createLedgerHarness();
  try {
    const result = runScript(
      'model-automation-report.mjs',
      ['--json', '--path', harness.ledgerPath],
    );
    assert.equal(result.status, 0);
    const payload = JSON.parse(result.stdout.trim());
    assert.equal(payload.status, 'empty');
    assert.equal(payload.totals.entries, 0);
    assert.equal(payload.files.every((entry) => entry.exists === false), true);
  } finally {
    fs.rmSync(harness.dir, { recursive: true, force: true });
  }
}

function testLedgerReportJsonErrorsRespectJsonFlag() {
  const result = runScript(
    'model-automation-report.mjs',
    ['--json', '--limit'],
  );
  assert.equal(result.status, 1);
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.error, 'flag_incompleto');
  assert.equal(payload.flag, '--limit');
}

function testSwarmJsonIncludesMetrics() {
  const result = runScript(
    'model-swarm.mjs',
    ['--json', '--agents=5', 'texto corto para consenso medido'],
  );
  assert.equal(result.status, 0, 'esperaba salida válida con métricas de swarm');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.engine, 'swarm');
  assert.equal(payload.agents, 5);
  assert.equal(typeof payload.consensusRatio, 'number');
  assert.equal(Array.isArray(payload.modelBreakdown), true);
  assert.equal(typeof payload.timing.totalMs, 'number');
  assert.equal(typeof payload.timing.routerTotalMs, 'number');
  assert.equal(typeof payload.timing.routerAverageMs, 'number');
  assert.equal(payload.taskMetrics.words, 5);
}

function testSwarmGuardsRecursiveFlow() {
  const result = runScript(
    'model-swarm.mjs',
    ['--json', '--auto', '--flow=swarm', 'texto para evitar recursion'],
  );
  assert.equal(result.status, 0, 'esperaba salida válida cuando se intenta auto-encadenar swarm');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.engine, 'swarm');
  assert.equal(payload.shouldExecute, false);
  assert.equal(payload.flow, 'swarm');
  assert.equal(payload.guardedReason, 'recursive_swarm_flow');
}

function testFlowMappingsExecuted() {
  const flows = ['build', 'web', 'test', 'ship', 'release', 'swarm', 'perfect'];
  const command = 'node -e "console.log(process.env.CP_TEST_FLOW)"';
  for (const flow of flows) {
    const result = runScript(
      'model-dispatcher.mjs',
      ['--json', `--flow=${flow}`, `texto que incluye ${flow}`],
      {
        TASK_COMMAND: command,
        CP_TEST_FLOW: flow,
      },
    );
    assert.equal(result.status, 0, `esperaba status 0 para flujo ${flow}`);
    const payload = extractJsonFromEnd(result.stdout);
    assert.equal(payload.flow, flow, `esperaba flow ${flow}`);
    assert.equal(payload.status, 'ok');
    assert.equal(payload.executed, command);
  }
}

function testFlowMappingsDryRun() {
  const flows = ['build', 'web', 'test', 'ship', 'release', 'swarm', 'perfect'];
  for (const flow of flows) {
    const result = runScript(
      'model-dispatcher.mjs',
      ['--json', '--dry-run', `--flow=${flow}`, `texto sin ejecutar para ${flow}`],
    );
    assert.equal(result.status, 0, `esperaba status 0 en dry-run para flujo ${flow}`);
    const payload = extractJsonFromEnd(result.stdout);
    assert.equal(payload.flow, flow, `esperaba flow ${flow} en dry-run`);
    assert.equal(payload.status, 'dry-run');
    assert.equal(typeof payload.command, 'string');
  }
}

function testRouterGuideText() {
  const result = runScript('model-router.mjs', ['--guide']);
  assert.equal(result.status, 0, 'esperaba salida de guía sin error');
  assert.ok(result.stdout.includes('Guía de uso por modelo'), 'la guía debería incluir cabecera');
  assert.ok(result.stdout.includes('gpt-5.3-codex-spark'), 'la guía debería incluir gpt-5.3-codex-spark');
}

function testRouterGuideJson() {
  const result = runScript('model-router.mjs', ['--guide', '--json']);
  assert.equal(result.status, 0, 'esperaba salida JSON de guía');
  const payload = JSON.parse(result.stdout.trim());
  assert.ok(Array.isArray(payload.modelos), 'esperaba array "modelos"');
  assert.equal(payload.modelos.length, 5, 'esperaba todos los modelos en la guía');
  assert.ok(payload.modelos.every((entry) => entry.id && entry.mejor_para), 'cada entrada debe incluir id y mejor_para');
}
