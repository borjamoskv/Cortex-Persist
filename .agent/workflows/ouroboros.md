---
description: "OUROBOROS-∞ — Diagnóstico, análisis de entropía y meta-cognición. Auto-evolución requiere aprobación humana."
---

# ∞ OUROBOROS-∞ — The Infinite Self

> **El skill que analiza tu proceso.** Diagnóstico y meta-cognición son seguros.
> Auto-evolución y mutación de código requieren **aprobación humana explícita**.

## ⚠️ Safety Classification

| Category | Risk | Auto-run | HITL Required |
|:---|:---:|:---:|:---:|
| **Scan / Diagnose / Reflect** | LOW | ✅ Safe | No |
| **Entropy Analysis** | LOW | ✅ Safe | No |
| **War Council (deliberation)** | LOW | ✅ Safe | No |
| **Evolve (code mutation)** | HIGH | ❌ Never | **Always** |
| **Fortress (hardening)** | MEDIUM | ❌ Never | **Always** |

---

## 🔮 Comandos Rápidos

| Comando | Qué hace | Risk |
|:---|:---|:---:|
| `ouro-genesis` | Scan + archaeology + war council + plan | LOW |
| `ouro-evolve [target]` | Mejora + causal reasoning (⚠️ requires HITL) | HIGH |
| `ouro-diagnose [symptom]` | 5 Whys + blast radius + prevention | LOW |
| `ouro-fortress [project]` | Hardening de 5 capas (⚠️ requires HITL) | MEDIUM |
| `ouro-reflect` | Meta-cognición forzada | LOW |
| `ouro-pulse` | Entropía rápida (2 min) | LOW |
| `ouro-why "..."` | 5 Whys express | LOW |
| `ouro-council "..."` | War Council spot | LOW |
| `ouro-adversary [plan]` | Red Team un plan (analysis only) | LOW |
| `ouro-timeline [file]` | Arqueología temporal | LOW |
| `ouro-entropy [project]` | Entropía detallada | LOW |
| `ouro-learn` | Extraer learnings → CORTEX | LOW |

---

## ⚡ PROTOCOLO GENESIS-∞ (Despertar Completo)

### Paso 1 — Environment Scan

```bash
# Git state
git status --short
git log --oneline -10

# Running processes
ps aux | grep -E 'python|node|swift|cargo' | grep -v grep | head -10

# CORTEX state (if available)
cd ~/cortex && .venv/bin/python -m cortex.cli export 2>&1 | tail -5
```

### Paso 2 — Temporal Archaeology

```bash
# Historia del proyecto
git log --oneline -20
git log --stat -5

# Decisiones previas en CORTEX
cd ~/cortex && .venv/bin/python -m cortex.cli search "type:decision" --limit 10 2>/dev/null
```

### Paso 3 — CORTEX Deep Recall (Error Memory)

```bash
# Errores previos
cd ~/cortex && .venv/bin/python -m cortex.cli search "type:error" --limit 10 2>/dev/null

# Meta-learnings previos
cd ~/cortex && .venv/bin/python -m cortex.cli search "type:meta_learning" --limit 10 2>/dev/null
```

### Paso 4 — Entropy Analysis

Medir las 7 dimensiones de entropía:

```bash
# File Entropy (archivos > 300 LOC)
find . -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.swift" | xargs wc -l 2>/dev/null | sort -rn | head -20

# Ghost Entropy (ghosts activos)
cat ~/.cortex/context-snapshot.md 2>/dev/null | grep -i ghost | head -10

# Branch Entropy
git branch -a --sort=-committerdate | head -15

# Import Entropy (Python: imports no usados)
ruff check . --select F401 2>/dev/null | head -20
```

### Paso 5 — War Council

Presentar hallazgos y deliberar:

1. **PRESENTAR**: Resumir estado en ≤3 frases con datos.
2. **DELIBERAR**: Proponer 2-3 estrategias diferentes.
3. **CHALLENGE (Red Team)**:
   - "¿Qué pasa si esta estrategia falla en el paso 3?"
   - "¿Cuál es el peor caso?"
   - "¿Hay un edge case que no estamos viendo?"
4. **MERGE**: Tomar la mejor estrategia superviviente.
5. **COMMIT**: Documentar la decisión en `implementation_plan.md`.

### Paso 6 — Battle Plan (DRY-RUN by default)

Generar `implementation_plan.md` con:
- Score de entropía inicial
- Target de entropía
- Waves de ejecución con checkpoints
- Adversarial challenges sobrevividas
- Exit criteria
- **Estimated cost** (API calls, subagents, time)

> ⚠️ **Battle Plan is OUTPUT ONLY.** No code is mutated. Execution requires explicit `/ouro-evolve` with HITL approval.

---

## ⚡ PROTOCOLO EVOLVE (Mejora Consciente)

> **⚠️ P1 GATE: This protocol mutates code. It MUST NOT auto-run.**
> **Branch requirement: All evolve operations on `feature/*` or `refactor/*` branches only.**

### Pre-flight Check

Before any evolution:
```bash
# Verify we are NOT on a protected branch
BRANCH=$(git branch --show-current)
if [[ "$BRANCH" == "main" || "$BRANCH" == release/* ]]; then
  echo "❌ ABORT: Cannot evolve on protected branch '$BRANCH'"
  echo "Create a feature branch first: git checkout -b refactor/ouro-$(date +%Y%m%d)"
  exit 1
fi
```

### Paso 1 — Diagnóstico Enhanced (X-Ray 13D + Causal + Entropy)

```
Causal Layer:
→ ¿POR QUÉ existe la deuda técnica encontrada?
→ ¿CUÁNDO se introdujo? (git log -S)
→ ¿QUIÉN la introdujo y en qué contexto? (git blame)

Entropy Layer:
→ ¿La mejora reducirá o aumentará la entropía?
→ ¿Cuántos archivos nuevos vs eliminados?
→ ¿La abstracción nueva justifica su peso?
```

### Paso 2 — Red Team el Plan

Antes de ejecutar cada ola, atacar:
- **¿Puedes hacer lo mismo en menos archivos?**
- **¿Hay un cambio que haga innecesarios 3 de los demás?**
- **¿Qué rompe si este cambio falla a medias?**

### Paso 3 — HITL Confirmation

> "🔧 EVOLVE plan ready. Changes affect N files. Estimated impact: [LOW/MEDIUM/HIGH]. Proceed? (yes/no)"

Only after explicit human approval → execute.

### Paso 4 — Ejecución Adaptativa

- Medir entropía entre olas (no solo score).
- Si entropía aumenta → PARAR y simplificar.
- Si una ola falla → Causal analysis ANTES de retry.

### Paso 5 — Meta-Reflection Post-Sesión

Automático al terminar. Ver protocolo REFLECT abajo.

---

## ⚡ PROTOCOLO DIAGNOSE (Diagnóstico Causal)

### Paso 1 — Capturar Síntoma

```
SÍNTOMA EXACTO: [descripción precisa]
EVIDENCIA: [error message, log, screenshot]
DESDE CUÁNDO: [primera vez observado]
REPRODUCIBLE: [sí/no + steps]
```

### Paso 2 — Temporal Bisect

```bash
# ¿Cuándo empezó a fallar?
git log --oneline -20
# Si binario: git bisect start
# Si no: razonar cuándo cambió basándose en logs
```

### Paso 3 — 5 Whys

```
1. ¿POR QUÉ falla? → [respuesta con evidencia]
2. ¿POR QUÉ [causa 1]? → [respuesta con evidencia]
3. ¿POR QUÉ [causa 2]? → [respuesta con evidencia]
4. ¿POR QUÉ [causa 3]? → [respuesta con evidencia]
5. ¿POR QUÉ [causa 4]? → ROOT CAUSE: [causa raíz]
```

### Paso 4 — Blast Radius

```bash
# ¿Qué más afecta la causa raíz?
grep -rn "[patrón de la causa raíz]" --include="*.py" --include="*.js" --include="*.swift"
```

### Paso 5 — Fix + Prevention

```
FIX: [solución que ataca la causa raíz, no el síntoma]
PREVENT: [test, hook, lint rule, o documentación que evite recurrencia]
```

### Paso 6 — CORTEX Record

```bash
cd ~/cortex && .venv/bin/python -m cortex.cli add --type error \
  --content "SYMPTOM: ... | ROOT: ... | FIX: ... | PREVENT: ..." \
  --tags "ouroboros,diagnose,PROJECT"
```

---

## ⚡ PROTOCOLO REFLECT (Meta-Cognición)

### Ejecutar al final de CADA sesión significativa

```
SESSION METRICS:
→ Files modified: [N]
→ Tests added/fixed: [N]
→ Errors found: [N]
→ Backtrack count: [N]
→ Tool calls total: [N]
→ Parallel opportunities used: [%]

EFFICIENCY: [1-10]
  ¿Cuántos tool calls fueron necesarios vs usados?

PRECISION: [1-10]
  ¿Cuántas veces deshice algo?

KEY LEARNINGS:
  1. [learning 1]
  2. [learning 2]
  3. [learning 3]

STRATEGY EVOLUTION:
  → ¿Mi estrategia inicial fue correcta? [sí/no + por qué]
  → ¿Qué haría diferente? [cambio concreto]

TRANSFER:
  → ¿Algo aplica a otro proyecto? [bridge si aplica]
```

### Persistir en CORTEX

```bash
cd ~/cortex && .venv/bin/python -m cortex.cli add --type meta_learning \
  --content "SESSION [fecha]: efficiency=[N]/10, precision=[N]/10, key_learning='[más importante]', transfer='[si aplica]'" \
  --tags "ouroboros,meta,SESSION_PROJECT"
```

---

## 📊 Entropía Quick Reference

| Métrica | Comando de Medición | Sano | Alarma |
|:---|:---|:---:|:---:|
| **Files > 300 LOC** | `find . -name "*.py" \| xargs wc -l \| awk '$1>300'` | < 10% | > 25% |
| **Unused imports** | `ruff check . --select F401` | < 3% | > 10% |
| **Stale branches** | `git branch -a --sort=-committerdate` | < 20% stale | > 40% |
| **Open ghosts** | `grep ghost context-snapshot.md` | < 5 | > 10 |
| **Psi markers** | `grep -rE 'HACK\|FIXME\|WTF\|TODO'` | 0 | > 5 |
| **Commit entropy** | `git log --oneline -20 \| grep -vc test` | < 40% sin test | > 60% |

---

**Versión:** 2.0.0 — The Infinite Self (Hardened)
*Diagnóstico libre. Evolución controlada.*
