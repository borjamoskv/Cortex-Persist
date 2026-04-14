import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export function resolveAutomationRunId(env = process.env) {
  const existing = String(env.MODEL_AUTOMATION_RUN_ID || '').trim();
  return existing || crypto.randomUUID();
}

export function maybeWriteAutomationLedger(entry, env = process.env, cwd = process.cwd()) {
  const config = resolveLedgerConfig(env, cwd);
  if (!config.enabled) {
    return { enabled: false };
  }

  const payload = JSON.stringify({
    timestamp: new Date().toISOString(),
    version: 1,
    ...entry,
  });
  const bytes = Buffer.byteLength(`${payload}\n`, 'utf8');

  try {
    fs.mkdirSync(path.dirname(config.path), { recursive: true });
    const rotated = rotateIfNeeded(config.path, config.maxBytes, bytes);
    fs.appendFileSync(config.path, `${payload}\n`, 'utf8');

    return {
      enabled: true,
      written: true,
      path: config.path,
      bytes,
      rotated,
    };
  } catch (error) {
    return {
      enabled: true,
      written: false,
      path: config.path,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

export function resolveLedgerConfig(env = process.env, cwd = process.cwd()) {
  const pathValue = String(env.MODEL_AUTOMATION_LEDGER_PATH || '').trim();
  const enabledByFlag = isTruthy(env.MODEL_AUTOMATION_LEDGER_ENABLED);
  const enabled = !isTruthy(env.MODEL_AUTOMATION_LEDGER_SKIP) && (enabledByFlag || Boolean(pathValue));
  const resolvedPath = pathValue
    ? (path.isAbsolute(pathValue) ? pathValue : path.resolve(cwd, pathValue))
    : path.resolve(cwd, '.cortex', 'model-automation-ledger.jsonl');

  return {
    enabled,
    path: resolvedPath,
    maxBytes: parsePositiveInt(env.MODEL_AUTOMATION_LEDGER_MAX_BYTES, 262144),
  };
}

function rotateIfNeeded(targetPath, maxBytes, incomingBytes) {
  if (!fs.existsSync(targetPath)) {
    return false;
  }

  const currentSize = fs.statSync(targetPath).size;
  if (currentSize + incomingBytes <= maxBytes) {
    return false;
  }

  const backupPath = `${targetPath}.1`;
  fs.rmSync(backupPath, { force: true });
  fs.renameSync(targetPath, backupPath);
  return true;
}

function parsePositiveInt(value, fallback) {
  const parsed = parseInt(String(value || ''), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function isTruthy(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return normalized === '1' || normalized === 'true' || normalized === 'yes' || normalized === 'on';
}
