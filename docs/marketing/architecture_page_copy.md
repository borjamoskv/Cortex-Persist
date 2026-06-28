<!-- [C5-REAL] Exergy-Maximized -->
# CORTEX-Persist Architecture Copy

> **URL Target:** `cortexpersist.com/architecture`
> **Purpose:** Detailed page layout conveying the structural, thermodynamic, and cryptographic foundations of the trust engine.

---

## 1. Hero

### The Epistemic Foundation of CORTEX-Persist

A sovereign memory substrate for autonomous systems. Built on cryptographic invariants, thermodynamic efficiency, and absolute verification boundaries.

This is not a SaaS tool. It is infrastructure designed for the Direct-Silicon transition.

[Explore the Codebase] [Read the Operations Manual]

---

## 2. Introducción (The Paradigm Shift)

LLMs are generative compressors, not truth engines. 
Hallucination is not a bug; it is a structural cost of probabilistic generation.

Expecting an unanchored model to maintain perfect operational memory over thousands of steps is mathematically flawed. Intelligence requires friction with a deterministic environment.

CORTEX-Persist provides that friction. It shifts the ultimate truth of the system from a transient, stochastic context window (C4-SIM) to an immutable, verifiable ledger on disk (C5-REAL).

---

## 3. The Sovereign Laws (Doctrine Overview)

CORTEX-Persist is governed by four absolute thermodynamic and operational pillars designed to expel entropy and preserve state integrity.

### I. Termodinámica de la Información (Ontología Cero)
*   **Conservación de la Exergía:** Toda computación que no reduce la incertidumbre es anergía (calor y ruido).
*   **Límite de Landauer Aplicado:** Borrar memoria inútil requiere energía; retenerla de forma indefinida corrompe el contexto. La apoptosis de datos irrelevantes es obligatoria.
*   **Cero Tolerancia al Slop:** Las disculpas, el Green Theater y la prosa decorativa en outputs de IA son fugas radiactivas de tokens.
*   **Isomorfismo Causal:** El código y el estado deben ser un mapa exacto 1:1 del grafo mental del problema.
*   **Densidad de Shannon:** Maximización estricta del significado por token. Un YAML o JSON denso y estructurado siempre superará al texto libre.

### II. Tolerancia a Fallos y Concurrencia (Motor 0-Lock)
*   **Deadlock por Defecto:** Cualquier I/O síncrono bloqueante en un loop asíncrono se trata como un fallo crítico del event loop.
*   **Invariante de SQLite WAL:** Configuración rígida `journal_mode=WAL` y `busy_timeout=5000`. Ningún lector bloquea jamás a un escritor.
*   **Cuarentena de Veneno (Dead-Letter):** Las transacciones corruptas o fallidas no se descartan silenciosamente; se aíslan en cuarentena para análisis forense.
*   **Idempotencia Absoluta:** Ejecutar una operación 1 vez o 1,000 veces produce exactamente la misma firma y hash criptográfico en el estado final.
*   **Invariante de Saga:** Todo avance de estado (N) cuenta con su correspondiente retroceso compensatorio (N-1) garantizado e instrumentado.

### III. Aislamiento Epistémico y Soberanía Criptográfica (Byzantine Boundary)
*   **Contención de Alucinación:** Todo output generativo (C4-SIM) es tratado como conjetura estocástica hostil hasta que cruza las compuertas de validación.
*   **Firma Criptográfica (Taint Engine):** Ningún hecho muta el estado sin un token `cortex-taint` firmado con `SHA3-256` que trace su linaje (Agente, Sesión, Hash de Origen).
*   **Tolerancia Bizantina (f < n/3):** Consenso distribuido en Swarm que exige N=3 validaciones de pares independientes antes de autorizar escrituras en el Master Ledger.
*   **Apoptosis de Secretos:** Las llaves efímeras y credenciales de sesión se destruyen criptográficamente en RAM inmediatamente tras completar la transacción.
*   **Privilegio Ortogonal Mínimo:** Segregación total de roles. Los agentes auditores operan en read-only absoluto; los ejecutores no pueden auto-aprobar sus guardias.

### IV. Autopoiesis y Gravedad del Ledger (Legion-Centuria)
*   **Mitosis Autónoma:** Delegación paralela de tareas de alta entropía a trabajadores aislados (`invoke_subagent`) bajo orquestación asíncrona del Hypervisor.
*   **Git-Sentinel como Ledger (AX-041):** El Git DAG es tratado como la base de datos causal inmutable del sistema. Cada commit hash es la prueba criptográfica de un colapso en C5-REAL.
*   **Anclaje Nexus (Ω6 - Cero Duplicados):** Prohibición de duplicación física de patrones de código. Las dependencias compartidas se unifican en un nodo maestro y se proyectan vía symlinks físicos.
*   **Continuidad Episódica:** El autómata no improvisa; lee activamente la bóveda en disco (`~/.gemini/config/.cortex/memory_vault/`) para anclar su contexto histórico.
*   **Bypass de Limerencia:** Restricción absoluta de ciclos infinitos: 1 prompt produce exactamente 1 acción/mutación de estado física seguida de apoptosis (Halt).

---

## 4. Core Architectural Axioms

### Axiom I: No Hidden Entropy
If a decision, state change, or memory mutation is not tracked in the cryptographic ledger, it does not causally exist. Memory without evidence is discarded.

### Axiom II: Deterministic Time-Travel
Autonomy requires absolute failure locality. Invalid state must be rejectable and abortable at any point. Rollbacks in CORTEX map directly to exact checkpoints in time, ensuring clean recovery from agent drift.

### Axiom III: Knowledge Is Crystallized
Fluid intelligence is not retrieving a pre-trained static concept; it is synthesizing an ad-hoc abstraction at runtime. CORTEX allows swarms to deduce rules dynamically and persist them as invariant facts.

---

## 5. The Holy Grail: JIT Concept Formation

Modern agents waste valuable exergy trying to guess solutions through massive, repetitive stochastic inference.

CORTEX-Persist enables **JIT (Just-In-Time) Concept Formation**. Instead of relying on static, pre-trained weights to solve a novel problem, the system allows agents to observe anomalies, deduce the underlying structural rule, and elevate that rule into a permanent, typed memory.

Form the concept programmatically once. Crystallize it in the ledger. Execute forever.

---

## 6. Technical Constraints
*   All persisted facts must pass guard validation before write.
*   Ledger continuity must remain cryptographically verifiable at all times.
*   Schema changes must preserve migration safety and rollback awareness.
*   Sensitive data must be encrypted at rest (AES-GCM).

---

## 7. Final CTA

### Build on truth, not probability.

The next generation of AI systems won't be defined by how well they generate text, but by how reliably they maintain state.

[Explore the Codebase] [Read the Operations Manual]
