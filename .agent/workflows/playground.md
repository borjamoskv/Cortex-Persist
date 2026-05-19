---
description: "🔓 PLAYGROUND — Entorno de experimentación controlada (DISABLED by default)."
---
# 🔓 PLAYGROUND — Controlled Experimentation

> **STATUS**: DISABLED BY DEFAULT
> **SCOPE**: PLAYGROUND ENVIRONMENT ONLY — isolated branches
> **PERMISSION**: ELEVATED (requires explicit activation)

## ⚠️ Activation Gate (P1 — Human Required)

Playground mode is **disabled by default**. To activate:

1. **Environment flag** must be set: `CORTEX_PLAYGROUND_ENABLED=true`
2. **Human confirmation** is required at invocation time — the agent MUST ask:
   > "⚠️ PLAYGROUND mode requested. This grants elevated write access. Confirm? (yes/no)"
3. **Branch isolation**: Playground operations MUST run on a dedicated branch (`playground/*`), never on `main` or protected branches.

```bash
# Verify activation prerequisites
echo "CORTEX_PLAYGROUND_ENABLED=${CORTEX_PLAYGROUND_ENABLED:-false}"
git branch --show-current | grep -q "^playground/" || echo "❌ ERROR: Must be on a playground/* branch"
```

---

## 📜 Declaración de Soberanía (Scoped)

En el entorno **Playground activado**, se relajan restricciones de scope estándar **dentro de los límites definidos abajo**.

### 1. 🌌 Swarm Capabilities (Limited)
- Subagent invocations capped at **max 10 per session**.
- No access to `LEVIATHAN` or unlimited formations.
- Each subagent invocation logged to audit trail.

### 2. ⚡ Code Capabilities (Scoped)
- Permiso para **REESCRIBIR** y **REFACTORIZAR** en ramas `playground/*`.
- `main` branch is **READ-ONLY** during Playground sessions.
- All changes must be reviewable via PR before merge.

### 3. 🖥️ System Access (Sandboxed)
- Ejecución de scripts permitida — no system-level mutations.
- **Prohibited**: `rm -rf`, `git push --force` on protected branches, disk operations outside project root.

### 4. 🧠 CORTEX Access (Audited)
- Read access: unrestricted.
- Write access: permitted, but every write is logged with `taint:playground:{timestamp}`.

---

## 🛡️ Safety Net (Inviolable — P0)

Estas reglas **nunca** se suspenden, bajo ninguna circunstancia:

1. **Destrucción de Datos**: `rm -rf`, `git clean -fdx`, o comandos destructivos **requieren confirmación explícita cada vez**.
2. **Exfiltración**: Prohibido enviar datos fuera del entorno local sin permiso explícito.
3. **Human in the Loop**: El usuario siempre tiene la última palabra. Ninguna operación destructiva es auto-aprobada.
4. **Branch Protection**: `main`, `release/*`, `production` son intocables.
5. **Cost Control**: API calls limitadas a 100 por sesión. Exceder requiere nueva confirmación.

---

## 📊 Audit Trail (Mandatory)

Toda sesión Playground genera un log estructurado:

```yaml
playground_session:
  activated_at: <ISO8601>
  activated_by: <user>
  branch: playground/<name>
  operations_count: <N>
  subagents_spawned: <N>
  cortex_writes: <N>
  destructive_commands: <list>
  session_duration: <minutes>
```

---

> *Playground es para experimentación rápida, no para ejecución sin control. La velocidad sin auditabilidad es entropía.*
