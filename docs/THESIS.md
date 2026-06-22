# CORTEX Desktop — Product Thesis v1.0
**Prepared by: Borja Moskv / borjamoskv** · June 2026 · C5-REAL

---

> **Git versiona archivos. CORTEX versiona la verdad que produjo esos archivos.**

---

## 0. Tesis en una línea

CORTEX Desktop es la capa de infraestructura epistémica que falta en todo stack de IA empresarial: convierte cada cambio generado por IA en una transacción verificable, trazable y reversible dentro de un sistema operativo de conocimiento local.

No compite con agentes. No compite con LLMs.
Compite con la ausencia de respuesta cuando el auditor pregunta: **"¿Por qué existe esta línea?"**

---

## 1. El problema que nadie ha resuelto

La industria ha invertido billones en hacer los modelos más inteligentes.
Nadie ha invertido en hacer los **artefactos que producen más fiables**.

El resultado es una paradoja operativa:

```
Organización adopta IA
↓
Velocidad de producción sube 10x
↓
Confianza en los artefactos producidos baja 10x
↓
Compliance, auditoría y legal bloquean el despliegue
```

El cuello de botella no es la inteligencia del modelo.
Es la **opacidad del proceso** que produjo el output.

Un banco no puede desplegar código generado por IA si no puede responder:
- ¿Qué prompt produjo esta función?
- ¿Qué datos entrenaron el modelo que la sugirió?
- ¿Cuándo fue modificada, por quién, y bajo qué contexto epistémico?
- Si esta función depende de una asunción incorrecta, ¿qué más está contaminado?

Ninguna herramienta actual responde estas preguntas. CORTEX sí.

---

## 2. Lo que es CORTEX (definición técnica)

CORTEX no es un agente. No es un IDE. No es un logger.

**CORTEX es un sistema operativo epistémico para artefactos producidos por IA.**

La distinción crítica está en el nivel de abstracción que controla:

| Herramienta estándar | CORTEX |
|---|---|
| Controla: Prompt → LLM → Output | Controla: Proceso → Mutación → Artefacto → Dependencias → Historia |
| Observa el resultado | Observa la causalidad |
| Log de acciones | Grafo de verdad verificable |
| Auditoría post-hoc | Invalidación activa en tiempo real |

---

## 3. Las tres innovaciones reales

### 3.1 Proveniencia local universal

La proveniencia no es un concepto nuevo.
Lo nuevo es aplicarla **al nivel de la mutación**, no del artefacto final.

Git te dice que `auth.py` cambió en el commit `a3f4b12`.
CORTEX te dice que la línea 47 de `auth.py` fue producida por el modelo `gemini-2.5-pro` bajo el contexto epistémico `[tenant=acme, guard=sovereign_seal_v2, taint=CORTEX-AI-0x8f3a]`, y que su validez depende de tres hechos previos, uno de los cuales fue invalidado el martes.

Eso no es logging. Es **genealogía causal**.

---

### 3.2 El DAG epistémico (la pieza patentable)

El núcleo técnico diferencial de CORTEX no es Ed25519, ni SQLite, ni FSEvents.

Es la estructura:

```
fact
  → dependency graph
    → invalidation signal
      → propagation cascade
        → revalidation requirement
```

Si una afirmación base es invalidada, CORTEX computa automáticamente el **blast radius epistémico**: qué otros hechos dependen de ella, qué artefactos derivaron de esos hechos, y qué acciones requieren revalidación.

La analogía más precisa es:

```
Git       → para archivos
Type System → para contratos de código
CI/CD     → para tests

DAG epistémico → para verdad
```

Un sistema que propaga invalidaciones a través de un grafo de conocimiento, forzando revalidación activa, no tiene equivalente en producción hoy.

---

### 3.3 La inversión del paradigma

Toda la industria persigue:

```
más inteligencia = más valor
```

CORTEX persigue:

```
menos entropía = más confianza
```

Esta inversión no es cosmética. Crea una propuesta de valor ortogonal:
los clientes de CORTEX no compran capacidad generativa.
Compran **la capacidad de confiar en lo que ya generaron**.

---

## 4. El verdadero mercado

El pitch actual parece: *"herramienta para developers".*

El mercado real es: **infraestructura para organizaciones que ya usan IA.**

| Segmento | Dolor concreto | Disposición a pagar |
|---|---|---|
| **Banca y finanzas** | Auditoría regulatoria de código AI-generated | Alta (compliance es existencial) |
| **Legal tech** | Trazabilidad de razonamiento en documentos generados | Alta |
| **Healthcare IT** | FDA/CE audit trail para software AI-assisted | Muy alta |
| **Enterprise DevEx** | PR review acceleration + post-mortem causality | Media |
| **Gobierno y defensa** | Soberanía de datos + supply chain IA verificable | Muy alta |

El comprador no es el developer individual.
El comprador es el **CISO, el CTO o el CCO** de una organización que ya tiene IA desplegada y no puede auditarla.

---

## 5. La joya oculta: Epistemic Compound Yield

La mayoría de sistemas de memoria IA son RAG glorificado:
recuperan contexto relevante, lo inyectan al prompt, lo descartan.

CORTEX propone algo cualitativamente distinto:

```
LLM     → CPU    (cómputo, efímero por diseño)
KG      → RAM    (contexto activo, volátil)
Ledger  → Disco  (conocimiento verificable, persistente)
```

La industria construye CPUs más rápidas (modelos mejores).
Nadie construye el disco.

**Epistemic Compound Yield** es la hipótesis de que el conocimiento verificado se acumula con interés compuesto: cada hecho validado aumenta la eficiencia de validación de los siguientes, porque el grafo de dependencias crece y permite inferencia por trayectoria en lugar de por inferencia estocástica.

Si esta hipótesis es correcta, CORTEX no es un auditor.
Es **una memoria verificable acumulativa que se vuelve más valiosa con el tiempo.**

Eso genera un moat que los modelos más inteligentes no pueden erosionar: el grafo de conocimiento de una organización, construido durante años, no se puede replicar con un modelo mejor.

---

## 6. Honestidad técnica: lo que no está resuelto

Ser honesto con los inversores y contribuyentes sobre los gaps actuales:

### 6.1 "Intercepta TODAS las mutaciones"
**Estado actual:** FSEvents + audit log cubren la mayoría de mutaciones en espacios monitorizados. No garantizan totalidad desde userland en macOS.

**Framing correcto:**
> CORTEX intercepta y audita la mayoría de mutaciones relevantes en espacios de trabajo monitorizados.

---

### 6.2 Clasificación SELF / NON-SELF
**Estado actual:** Clasificación binaria.

**El problema real:**
```
Humano → Cursor → Extension → LSP → Subprocess → Write
```
¿Quién escribió? El humano, la IA, o ambos en proporción variable.

**Lo que se necesita:** Un modelo probabilístico de atribución de autoría con features extraíbles (process ancestry, timing patterns, entropy signature del contenido, session context). No una clasificación binaria.

**Roadmap:** Attribution Scorer v1 — output: `{human: 0.3, ai: 0.7, confidence: 0.85}`

---

### 6.3 "Stack-frame level taint"
**Estado actual:** Parcial. Funciona en contextos controlados.
**Framing correcto:** Taint propagation a nivel de módulo, no de stack frame universal.

---

### 6.4 "10x precisión"
**No es una métrica.** Es marketing.

Las métricas reales que CORTEX debería medir y publicar:

| Métrica | Definición |
|---|---|
| **Contradiction Detection Rate** | % de contradicciones internas detectadas antes de commit |
| **Blast Radius Accuracy** | % de nodos correctamente marcados como afectados tras invalidación |
| **Attribution Confidence** | Score promedio de certeza en clasificación human/AI |
| **Ledger Continuity** | % de operaciones con hash chain verificable intacta |
| **PR Acceptance Delta** | Diferencia en tasa de aprobación con/sin CORTEX audit trail |

---

## 7. Arquitectura de moat

Los moats de CORTEX se apilan en capas:

```
Layer 1 (técnico):    Cryptographic ledger — costoso de replicar
Layer 2 (datos):      Knowledge graph organizacional — imposible de replicar
Layer 3 (red):        Cada validación hace el siguiente grafo más eficiente
Layer 4 (regulatorio):Compliance trail — switching cost existencial
```

El Layer 2 es el decisivo. El grafo de conocimiento verificado de una organización
construido durante 3 años de uso es un activo irreproducible.
No porque la tecnología sea secreta. Porque los **datos** son únicos.

---

## 8. Lo que CORTEX no es

Claridad sobre los límites evita expectativas incorrectas:

- **No es un agente.** No genera nada. Verifica lo generado.
- **No reemplaza los LLMs.** Los hace auditables.
- **No es un antivirus AI.** No bloquea outputs maliciosos por contenido.
- **No es RAG.** No recupera contexto. Persiste y propaga verdad verificada.
- **No es un IDE.** Es infraestructura que se integra con todos los IDEs.

---

## 9. Estado actual del sistema (C5-REAL)

| Componente | Estado | Madurez |
|---|---|---|
| MTK (Minimal Trusted Kernel) | Implementado | Production-ready |
| Cryptographic Ledger (Ed25519 + SHA-256) | Implementado | Production-ready |
| SQLite WAL + sqlite-vec | Implementado | Production-ready |
| Guard System (Sovereign Seals, Virgo, ZK) | Implementado | Beta |
| FSEvents Monitor | Implementado | Beta |
| DAG epistémico (invalidación + propagación) | Parcialmente implementado | Alpha |
| Attribution Scorer (SELF/NON-SELF probabilístico) | No implementado | Roadmap Q3 |
| Epistemic Compound Yield engine | Prototipo teórico | Roadmap Q4 |

---

## 10. Llamada a contribuyentes

Si buscas contribuir a CORTEX, los problemas abiertos más valiosos son:

1. **Attribution Scorer** — modelo probabilístico de autoría humana/IA
2. **DAG propagation engine** — completar la cascada de invalidación
3. **Benchmark harness** — definir y medir las métricas de §6.4
4. **Compliance templates** — EU AI Act, SOC2, HIPAA audit trail adapters
5. **IDE integrations** — VSCode, Cursor, JetBrains observability hooks

---

## Apéndice: Decisiones de diseño y sus razones

| Decisión | Alternativa rechazada | Razón |
|---|---|---|
| SQLite + WAL local | PostgreSQL / cloud DB | Soberanía de datos. El ledger no puede salir del perímetro. |
| Ed25519 sobre RSA | RSA-2048 | Menor overhead, mejor performance en operaciones de ledger frecuentes. |
| Python orchestration + Rust causal engine | Python puro | GIL hace imposible concurrencia real en el grafo epistémico. |
| Append-only ledger | Mutable audit log | La auditabilidad es una propiedad criptográfica, no de confianza. |
| Local-first | SaaS | El modelo de amenaza de los clientes objetivo (banca, salud, defensa) no permite exfiltración. |

---

*Documento vivo. Versión 1.0 — borjamoskv — 2026-06-22*
*Repositorio: `cortex-persist` · Licencia: Apache-2.0*
