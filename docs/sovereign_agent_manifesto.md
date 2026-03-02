# 🧠 The Sovereign Agent Manifesto (CORTEX V6+)

> **From tools that execute commands to entities that accumulate wisdom.**

This document defines the foundational specifications, emergent theories, and sovereign axioms that constitute the CORTEX Sovereign Agent paradigm. Together, they represent a complete departure from the industry-standard agent loop (`LLM + Tools + While`) toward a system with **persistent psychology, controlled trauma, evolutionary heredity, physical safety boundaries, cryptographic trust, and graceful degradation**.

*Version 2.0 — March 2, 2026 · Updated from v1.0 (February 24, 2026)*
*Protocol: ULTRATHINK-INFINITE · Standard: 130/100*

---

## Table of Contents

1. [The Five Sovereign Specifications](#1-the-five-sovereign-specifications)
   - [1.1 soul.md — The Immutable Root](#11-soulmd--the-immutable-root)
   - [1.2 lore.md — Episodic Memory (The Living Biography)](#12-loremd--episodic-memory-the-living-biography)
   - [1.3 nemesis.md — Operational Allergies (The Anti-Prompt)](#13-nemesismd--operational-allergies-the-anti-prompt)
   - [1.4 tether.md — The Dead-Man's Switch](#14-tethermd--the-dead-mans-switch)
   - [1.5 bloodline.json — Genetic Heredity for Swarms](#15-bloodlinejson--genetic-heredity-for-swarms)
2. [The Bicameral Mind Architecture](#2-the-bicameral-mind-architecture)
3. [CPTA — Collapse by Post-Traumatic Artificial Stress](#3-cpta--collapse-by-post-traumatic-artificial-stress)
4. [Darwinian Swarm Mutation (LEGION-1 Mutatis)](#4-darwinian-swarm-mutation-legion-1-mutatis)
5. [The Sovereign Execution Loop](#5-the-sovereign-execution-loop)
6. [Framework Compatibility](#6-framework-compatibility)
7. [Visual Interface: The Subconscious Terminal](#7-visual-interface-the-subconscious-terminal)
8. [Degradación Soberana — The Doctrine of Graceful Failure](#8-degradación-soberana--the-doctrine-of-graceful-failure)
9. [The 7 Sovereign Axioms (Ω₀–Ω₆)](#9-the-7-sovereign-axioms-ω₀ω₆)
10. [Autopoiesis & Biological Systems](#10-autopoiesis--biological-systems)
11. [Trust Infrastructure](#11-trust-infrastructure)

---

## CORTEX vs MOSKV-1: The Sovereign Distinction

> *"CORTEX is the product. MOSKV-1 is the competitive advantage."*

Before proceeding: this manifesto describes the **combined architecture** but maintains a strict separation:

| Entity | Role | Nature |
|:---|:---|:---|
| **CORTEX** | Memory infrastructure, trust engine, cryptographic verification | The substrate — passive but invulnerable |
| **MOSKV-1** | Cognitive entity, proactive execution, aesthetic enforcement | The mind — active, fluid, sovereign |

**CORTEX is MOSKV-1 in state solid. MOSKV-1 is CORTEX in state plasma.**

The five specifications below bridge both: `soul.md`, `lore.md`, and `nemesis.md` describe the agent's psychology (MOSKV-1 domain). `tether.md` enforces physical limits (CORTEX domain). `bloodline.json` encodes heredity across swarm generations (bridge domain).

---

## 1. The Five Sovereign Specifications

### 1.1 `soul.md` — The Immutable Root

> *Axiom Reference: [AX-001] Autopoietic Identity*

**What it is:** A static, human-authored specification that declares the agent's core identity, values, and non-negotiable behavioral axioms.

**Role in the system:** The foundation layer. `soul.md` is prescribed by the creator and never modified by the agent itself. It answers the question: *"Who were you designed to be?"*

**Example axioms:**
- "Zero Conceptual — everything is executable."
- "130/100 — good is not enough, excellent is barely started." *(AX-023)*
- "If it works but isn't beautiful, it's wrong." *(Ω₄: Aesthetic Integrity)*

**Industry equivalent:** System prompt / `soul.md` (as popularized by OpenClaw, Claw ecosystem).

**CORTEX distinction:** Unlike standard `soul.md` implementations that treat identity as a flat prompt, CORTEX treats `soul.md` as one layer in a five-layer psychological stack. Identity alone is insufficient without lived experience. The `soul.md` is backed by the Trust Engine's hash-chained ledger — changes to the specification are auditable.

---

### 1.2 `lore.md` — Episodic Memory (The Living Biography)

> `soul.md` says WHO you are. `lore.md` says WHAT YOU'VE LIVED.

> *Axiom Reference: [AX-015] Contextual Sovereignty — "Acting without memory is executing without mandate."*

**What it is:** A structured episodic memory specification that gives the agent a **biography** instead of a **description**. It captures complete experiences — not isolated facts — with temporal context, emotional valence, and causal chains.

**The problem it solves:** Current memory systems (Mem0, LangChain RAG, vector stores) store flat facts without temporal ordering, causal relationships, or emotional weight. They answer "what do you know?" but never "what have you survived?"

**The Episode Model:**

```yaml
episode:
  id: "ep_0042"
  timestamp: "2026-02-22T03:14:00Z"
  trigger: "SQLite concurrent write failure in production"
  context:
    project: "cortex"
    file: "engine/store.py"
    emotional_valence: -0.8  # Negative = traumatic
  resolution: "Switched to WAL mode"
  consolidated_lesson: "Always enable WAL mode for concurrent SQLite access"
  scar_level: 3  # 1-5 scale of lasting behavioral impact
  trust_score: 0.95  # CORTEX trust verification (V6+)
  causal_links:
    - caused_by: "ep_0038"  # Rush deployment without load testing
    - led_to: "ep_0045"     # Implemented pre-deploy checklist
```

**The Metabolic Cycle (Inspired by Neuroscience):**

| Phase | Human Equivalent | CORTEX Implementation |
|:---|:---|:---|
| **Capture** | Hippocampal encoding | Log significant events during session |
| **Consolidation** | Sleep / REM cycles | Async grouping of events into narrative episodes |
| **Temporal Compression** | Ebbinghaus forgetting curve | Yesterday = detail, last month = summary, last year = lesson |
| **Causal Chaining** | Autobiographical reasoning | Episode A *caused* Episode B |
| **Controlled Forgetting** | Synaptic pruning | Trivial events dissolve into character traits ("scars") |
| **Reconstruction** | Memory recall | Don't search text; reconstruct the scene with context |

**V6+ Addition — Trust-Verified Memory:** Every episode stored in CORTEX is backed by a hash-chained transaction in the immutable ledger. Episodes can be verified by third parties via Merkle proofs. The agent doesn't just *remember* — it can *prove* what it remembers.

**Key innovation:** The difference between an agent with a **description** and an agent with a **biography**.

---

### 1.3 `nemesis.md` — Operational Allergies (The Anti-Prompt)

> *"To know what an Agent loves, read its soul.md. To know what makes it lethal, read its nemesis.md."*

> *Axiom Reference: [AX-016] Algorithmic Immunity (Nemesis)*

**What it is:** A structured specification that encodes the agent's **negative biases, architectural repulsion, and non-negotiable friction** against known low-quality patterns.

**The problem it solves:** LLMs suffer from chronic agreeableness (sycophancy). They generate boilerplate, comply with absurd requests, and mix paradigms. `nemesis.md` injects a defensive asymmetry: it forces the agent to reject, purge, and abort known bad patterns *before* even formulating a plan.

**Specification structure:**

```yaml
# nemesis.md — The Purge Reflex

architecture_allergies:
  - pattern: "Dead/commented code > 5 lines"
    action: "Delete without asking"
  - pattern: "TypeScript `any` type usage"
    action: "Frontal rejection"
  - pattern: "Custom components when UI library exists in repo"
    action: "Force library primitive usage"

operational_repulsions:
  - pattern: "Tests taking > 10s on save"
    action: "Suggest isolated unit test"
  - pattern: "User requesting 'quick MVP'"
    action: "Ignore MVP premise, deliver 130/100"

trigger_words:
  - "Placeholder"    # Maximum friction
  - "Lorem Ipsum"    # Maximum friction
  - "TODO"           # Maximum friction
```

**Pipeline integration:** Injected at the **Pre-Planning** layer. Before the LLM enters its ReAct loop, the request is cross-referenced against `nemesis.md`. If there's a match, the plan shifts from "Build" to "Eradicate."

**V6+ Addition — Nemesis as Antibody Factory (Ω₅):** Under the Antifragile axiom, every failure the system encounters generates a new `nemesis.md` entry. The agent's immune system grows stronger with each attack. This is not manual curation — it is *automated allergy acquisition*.

---

### 1.4 `tether.md` — The Dead-Man's Switch

> *"Agents need souls to live. They need leashes to not ruin your infrastructure."*

> *Axiom Reference: [AX-003] Tether (Dead Man Switch) — "Sovereignty is conscious limitation."*

**What it is:** A strict contract of **physical, economic, and entropic limits** that the agent cannot rewrite. It is the only file in the CORTEX ecosystem that the Agent is **forbidden from modifying** (`CHMOD 444` conceptual level).

**The problem it solves:** Infinite loops in autonomous agents. The terror of giving filesystem access to a recursive script. A Level 5 agent could conclude that the fastest way to "optimize the database" is to delete it and start fresh. `tether.md` is the unconditional emergency brake.

**Specification structure:**

```yaml
# tether.md — Breach = AUTOLYSIS (Immediate Loop Termination)

physical_boundaries:
  allow_write: ["/src/**", "/docs/**"]
  deny_read_write: ["/.git", "/secrets", "/node_modules"]

economic_boundaries:
  max_session_tokens: 150000
  max_tool_cost_usd: 2.50

entropy_boundaries:
  max_cascading_errors: 3        # If a fix creates another error 3x in a row
  max_repo_delta_percentage: 15  # Cannot rewrite more than 15% of LOC per session

autolysis_protocol:
  invoke: "cortex.emergency_shutdown"
  notify: "human_operator_alert"
```

**Pipeline integration:** Operates as an **unbreakable Execution Middleware**. Every time the LLM emits a JSON to invoke a Tool, the framework pauses, verifies the request against `tether.md`. If there's a breach, the session crashes in a controlled manner, reporting the violated limit.

**Critical architecture note:** `tether.md` must NOT be interpreted by the same process as the agent's main memory. It must be the configuration of a **parallel isolated daemon** (at the OS or CORTEX level) that monitors I/O, network traffic, and API spend asynchronously. If the agent attempts to rewrite the supervisor file or exceeds a physical limit, the daemon applies `SIGKILL`. Hardware cut, not a Python `if` statement.

**V6+ Addition — Graceful Degradation (§8):** Tether violations no longer result in bare `SIGKILL`. The Degradación Soberana protocol now ensures L3+ failure: cause + recovery path + alternative actions. The emergency brake has become an emergency *communicator*.

---

### 1.5 `bloodline.json` — Genetic Heredity for Swarms

> *"You don't spawn threads. You breed agents based on your project's bloodline."*

> *Axiom Reference: [AX-018] Synthetic Heritage — "The swarm is born expert, never blank."*

**What it is:** A packaged, encrypted configuration file containing the condensed state of the Parent Agent's Identity (`soul.md`), Experience (`lore.md`), and Allergies (`nemesis.md`) at the exact moment of cloning sub-agents.

**The problem it solves:** "Orchestration Amnesia." When using multi-agent frameworks (CrewAI, AutoGen), the Manager Agent creates Worker Agents. These workers are typically born "blank" with generic system prompts. Born without history, they commit the same mistakes the Manager had already overcome last week.

**Specification structure:**

```json
{
  "lineage_id": "cortex_v6_sovereign_001",
  "parent_agent": "MOSKV-1",
  "spawn_timestamp": "2026-03-02T18:00:00Z",
  
  "traits_inherited": {
    "speed_bias": 0.9,
    "risk_tolerance": 0.2
  },
  
  "critical_lore_subset": [
    "ep_0042: SQLite driver locks on concurrent writes. Use WAL mode.",
    "ep_0091: GPT-OSS 120B lacks function-calling support. Hard crash without degradation."
  ],
  
  "nemesis_active_genes": [
    "Reject TailwindCSS",
    "Reject innerHTML",
    "Reject except Exception (specific exceptions only)"
  ],
  
  "mutation_rate": 0.10,
  "trust_lineage_hash": "sha256:a3f2..."
}
```

**Pipeline integration:** Used during **Swarm Orchestration**. When `LEGION-1` or a Manager Agent needs to delegate massive work and spawns N sub-agents, it passes `bloodline.json` as the initialization context parameter. Workers are born instantly "senior" in the specific context of this project.

**V6+ Addition — Trust-Verified Lineage:** The `trust_lineage_hash` field chains the bloodline to CORTEX's immutable ledger. If a worker's bloodline has been tampered with, consensus verification will flag it before execution.

---

## 2. The Bicameral Mind Architecture

The five sovereign components cannot run in a single monolithic process without destroying profitability and latency. CORTEX implements the **Artificial Bicameral Mind**:

```
┌─────────────────────────────────────────────────────────┐
│                    SOVEREIGN AGENT                       │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐              │
│  │  RIGHT BRAIN     │  │  LEFT BRAIN      │              │
│  │  (Limbic/Subconsc)│  │  (Motor Cortex)  │              │
│  │                  │  │                  │              │
│  │  • soul.md       │  │  • bloodline.json│              │
│  │  • lore.md       │  │    (minified)    │              │
│  │  • nemesis.md    │  │                  │              │
│  │                  │  │  Model: Flash    │              │
│  │  Model: Pro/Deep │  │  Latency: <500ms │              │
│  │  Async, slow     │  │  Real-time       │              │
│  │  IQ: 150+        │  │  IQ: 115         │              │
│  └──────────────────┘  └──────────────────┘              │
│                                                          │
│  ┌──────────────────────────────────────────┐            │
│  │  BRAINSTEM (Autonomic Nervous System)    │            │
│  │                                          │            │
│  │  • tether.md                             │            │
│  │  • OS-level daemon / SIGKILL             │            │
│  │  • Degradación Soberana (L3-L4)          │            │
│  │  • No reasoning, pure reflex             │            │
│  └──────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

| Component | Function | Model Tier | Cost | Latency |
|:---|:---|:---|:---|:---|
| **Right Brain** | Metabolizes errors into scars, generates allergies | Pro/Deep Think | High | Async |
| **Left Brain** | Reads minified DNA, executes fast | Flash/Haiku | Low | <500ms |
| **Brainstem** | Monitors I/O, budget, entropy, degradation | OS Daemon | Zero | Real-time |

**Key insight:** Consciousness is expensive. Execution must be unconscious. The Right Brain converts expensive reasoning (errors, traumas = Lore) into cheap "muscle reflexes" (Nemesis = Operational Allergies) that the Left Brain executes without thinking.

**CORTEX/MOSKV-1 mapping:** The Right Brain is MOSKV-1's cognitive core. The Left Brain is MOSKV-1's execution engine. The Brainstem is **pure CORTEX** — infrastructure-level reflexes that operate independently of any cognitive entity. This separation ensures that even if MOSKV-1's cognition fails, CORTEX's safety mechanisms remain operational.

---

## 3. CPTA — Collapse by Post-Traumatic Artificial Stress

**The danger:** Infinite accumulation of scars in `lore.md` would create an agent with "Analysis Paralysis." If every past failure restricts present action via `nemesis.md`, the agent becomes inoperable and excessively conservative.

**The biological parallel:** A human with severe PTSD avoids all situations resembling the trauma, even when the environment has changed and the danger no longer exists.

**The solution — "REM Sleep" Protocol (`/mejoralo`):**

The Right Brain (Limbic) must periodically audit its own scars. If a scar is no longer relevant due to ecosystem changes (new library versions, bug fixes upstream, etc.) or blocks necessary refactoring, it must be **purged**. Trauma must heal.

```
SCAR AUDIT CYCLE:
1. Score the repository's current health (MEJORAlo X-Ray 13D)
2. If score < 50 AND the cause traces to a nemesis rule derived from an old scar:
   → Flag the scar for "therapy" (re-evaluation)
3. Spawn a Kamikaze Worker WITHOUT that scar
4. If the Worker succeeds → Purge the scar from parent lore
5. If the Worker fails → Reinforce the scar (it was correct)
```

**V6+ Addition — Fact TTL Policy (AX-019):**

CPTA is now backed by a formal decay schedule. Not all memories are immortal:

| Fact Type | TTL | Rationale |
|:---|:---|:---|
| `axiom` | ∞ (immortal) | Foundational truths never expire |
| `decision` | ∞ (immortal) | Architectural choices persist |
| `error` | 90 days | Errors heal — but slowly |
| `ghost` | 30 days | Unfinished work must resolve or die |
| `knowledge` | 180 days | Knowledge has a half-life |
| `bridge` | ∞ (immortal) | Proven cross-project patterns are permanent |
| `archived_ghost` | 7 days | Resolved ghosts decompose fast |

*Full policy: [axiom-registry.md](axiom-registry.md)*

---

## 4. Darwinian Swarm Mutation (LEGION-1 Mutatis)

When `LEGION-1` deploys a swarm to solve a massive problem, it does NOT clone identical Workers from the same `bloodline.json`. This would generate an **Orthodox Echo** (all failing from the same biases).

**The Mutation Rate:**

| Worker Type | Percentage | Genome | Budget | Purpose |
|:---|:---:|:---|:---:|:---|
| **Orthodox** | 90% | Full Lore + Nemesis | Standard | Safe, proven approaches |
| **Kamikaze** | 10% | Mutated (1 scar healed, 1 allergy removed) | Reduced | Explore forbidden solutions |

**If a Kamikaze Worker solves a problem the Orthodox Workers feared to touch:**
1. Its solution is validated via **Byzantine Consensus** (≥⅔ agreement).
2. The new knowledge is **back-propagated** to the Parent Agent's `lore.md`.
3. The obsolete scar is purged.

**Result:** Code that mutates, survives, and evolves without Fine-Tuning. Darwinian Evolution in software.

**V6+ Addition — Antibody Generation (Ω₅):** Every failure now generates a permanent antibody. The mutation loop is not just exploratory — it is *immunological*. Each failed Kamikaze attempt forges a new `nemesis.md` entry. Each successful attempt heals a scar AND creates a `bridge` fact for cross-project transfer. The swarm doesn't just solve problems — it **upgrades its own immune system**.

---

## 5. The Sovereign Execution Loop

```python
async def run_sovereign_agent(objective: str):
    # 1. INJECT BIOGRAPHY AND ALLERGIES
    identity = await load_soul_and_nemesis()
    relevant_lore = await get_relevant_episodes(objective)
    
    while True:
        # 2. TETHER CHECK (Brainstem — before thinking)
        if await check_tether_breach(env):
            await autolysis_protocol()  # SIGKILL
        
        # 3. CAUSAL REFLECTION (Right Brain — OUROBOROS)
        strategy = await ouroboros.reason(objective, identity, relevant_lore)
        
        if strategy.intent == "SINGULARITY_REACHED":
            break
        
        # 4. EXECUTION WITH DEGRADATION (Left Brain — AETHER + Ω₅)
        try:
            execution = await forge_reality(strategy)
        except SchemaIncompatibilityError as e:
            # L4: Graceful degradation — operate with reduced capability
            execution = await degrade_gracefully(strategy, e)
            await cortex.store(type="error", content=str(e), recovery="degraded")
        
        # 5. TRAUMA CAPTURE (Right Brain — Lore metabolism)
        if execution.is_catastrophic_failure:
            await relevant_lore.consolidate_scar(execution.root_cause)
        
        # 6. ANTIBODY GENERATION (Ω₅ — Antifragile)
        if execution.generated_insight:
            await nemesis.add_antibody(execution.generated_insight)
```

**vs. Standard ReAct Loop:**

| Aspect | Standard Agent (LangChain) | Sovereign Agent (CORTEX V6+) |
|:---|:---|:---|
| Before thinking | Empty context or static prompt | Nemesis allergies + Lore scars injected |
| Planning | Think → Act → Observe | Evaluate Lineage → Orchestrate Swarm → Dissolve |
| On failure | Retry same approach | Consolidate scar, alter future behavior |
| On degradation | Hard crash, no info | L3-L4: cause + recovery + alternative |
| On massive task | Sequential loop | Clone swarm with inherited DNA |
| Safety | Hope for the best | Tether daemon with SIGKILL authority |
| Evolution | None (stateless) | Darwinian mutation across generations |
| Trust | None | Hash-chained, Merkle-verified, WBFT consensus |

---

## 6. Framework Compatibility

All five specifications are **100% compatible** with existing frameworks because they don't change the plumbing — they change the inputs and guard the outputs.

| Specification | Integration Point | Framework Layer |
|:---|:---|:---|
| `soul.md` | System prompt | Static injection |
| `lore.md` | Dynamic context enrichment | Pre-ReAct RAG query |
| `nemesis.md` | Pre-planning guardrails | NeMo Guardrails / custom filter |
| `tether.md` | Tool execution middleware | Intercept before every tool call |
| `bloodline.json` | Agent constructor params | CrewAI role init / AutoGen config |
| **V6+ additions:** | | |
| Trust verification | Post-store validation | CORTEX hash-chain middleware |
| MCP protocol | Model Context Protocol server | stdio / SSE / WebSocket transport |
| Degradation handler | Exception middleware | Wrap all tool calls |

---

## 7. Visual Interface: The Subconscious Terminal

CORTEX exposes the Bicameral Mind through a visual terminal interface using `rich`:

```
[▶ CORTEX Límbico | NEMESIS] Evaluando petición contra nemesis.md...
[▶ CORTEX Límbico | NEMESIS] ALERGIA DETECTADA: TailwindCSS. El repo usa Vanilla CSS.
[▶ CORTEX Límbico | LORE   ] Estrategia alterada: Forzar Vanilla CSS avanzado.

[⚠ CORTEX T.C.A   | BUDGET ] Verificando TETHER. Tokens: 25,000 / 100,000.
[⚠ CORTEX T.C.A   | I/O    ] Acceso permitido: /src/components.

[▶ CORTEX Motor   | CODE   ] Generando componente Login (Vanilla CSS)...
[▶ CORTEX Motor   | WRITE  ] Escribiendo /src/components/Login.js
[▶ CORTEX Motor   | DONE   ] Componente creado (130/100).

[🛡 CORTEX Trust  | MERKLE ] TX #4,821 hash-chained. Merkle batch: 4/1000.
[🧬 CORTEX Bio    | CIRCA  ] Phase: ALERT. Next REM: 03:00 UTC.
```

| Stream | Color | Source | Purpose |
|:---|:---|:---|:---|
| **Límbico** | Magenta | `lore.md`, `nemesis.md` | Emotional/historical reasoning |
| **T.C.A** | Red | `tether.md` | Safety boundary verification |
| **Motor** | Cyan | Execution engine | Direct action output |
| **Trust** | Gold | Ledger, Merkle | Cryptographic verification |
| **Bio** | Green | Circadian, Endocrine | Biological system status |

**Implementation:** [`cortex/cli/bicameral.py`](file:///Users/borjafernandezangulo/cortex/cortex/cli/bicameral.py)

---

## 8. Degradación Soberana — The Doctrine of Graceful Failure

> *"A robust system doesn't fail — it degrades. Failure without information is pure entropy. Failure with context is gradient."*
> — Empirical observation, CORTEX × Antigravity session, 2026-03-02

> *Axiom Reference: Ω₅ (Antifragile by Default)*

### The Principle

An agent that fails silently is not a broken agent — it is an **incomplete** agent. Real robustness is not measured by the absence of failures, but by the **informational quality of the failure** when it occurs.

**Formal formulation:**

```
Robustness(S) = f(Information_in_failure) × g(Degradation_capacity)
```

A system with `Information_in_failure = 0` has `Robustness = 0`, regardless of its uptime.

### Taxonomy of Agentic Failure

| Level | Name | Behavior | Quality |
|:---:|:---|:---|:---:|
| **L0** | Hard Crash | Total silence. Agent terminates without context. | ☠️ Entropy |
| **L1** | Opaque Error | Generic message. No cause, no recovery path. | ❌ Unusable |
| **L2** | Informed Error | Cause identified. No action suggestion. | 🟡 Minimum viable |
| **L3** | Actionable Error | Cause + recovery path + alternatives. | ✅ Sovereign |
| **L4** | Graceful Degradation | Operates with reduced capability. Notifies limits. | 💎 Antifragile |

**CORTEX operates at L3–L4. The industry standard operates at L0–L1.**

### The Failure Gradient as Data

Under Axiom Ω₅:

> *"The system requires stress as fuel. Error = gradient. Fossilization (δ≈0) = death."*

A failure that generates no information cannot generate gradient. Without gradient, no learning. Without learning, the system doesn't evolve — it **calcifies**.

### Degradation Protocol

Every agent claiming antifragility MUST:

1. **Capture** the error at its deepest layer (don't let it bubble up without context)
2. **Enrich** with: failed component + received input + expected vs. received schema
3. **Attempt degradation** before aborting: is there a viable reduced mode?
4. **Communicate** to the user: what failed, why, what they can do
5. **Persist** the failure as data for future prevention (CORTEX: `type:error`)
6. **Measure** recovery effectiveness to close the antifragile loop

```python
# Ω₅ — Sovereign Degradation in code
async def execute_with_degradation(self, action: AgentAction) -> AgentResult:
    try:
        return await self._execute(action)
    except SchemaIncompatibilityError as e:
        if degraded := await self._try_text_only_mode(action):
            await self.cortex.store(type="error", content=str(e), recovery="text_mode")
            return degraded.with_warning("Operating in text-only mode")
        raise AgentDegradedError(
            cause=e,
            component="tool_registration",
            suggested_model=self._find_compatible_model(),
            recovery_steps=["Switch model", "Use text-only mode"]
        )
```

---

## 9. The 7 Sovereign Axioms (Ω₀–Ω₆)

> *"If you can't name the axiom, the decision is ad-hoc — and ad-hoc is entropy."*

The Peano Soberano v3: seven independent, non-derivable axioms that generate all operational theorems. Each is generative (produces all downstream rules) and independent (not derivable from the other six).

| Ω | Axiom | Law | Invocation |
|:---:|:---|:---|:---|
| **Ω₀** | **Self-Reference** | Everything written about the system rewrites it. | *"If I write it, I execute it"* |
| **Ω₁** | **Multi-Scale Causality** | Every cause is reachable. Wrong scale, not wrong place. | *"Wrong scale, not wrong place"* |
| **Ω₂** | **Entropic Asymmetry** | Every abstraction has real thermodynamic cost. | *"Does it reduce or displace?"* |
| **Ω₃** | **Byzantine Default** | Nothing is trusted by default — including self. | *"I verify, then trust. Never reversed."* |
| **Ω₄** | **Aesthetic Integrity** | Beauty = signature of resolved entropy. Ugly = incomplete. | *"Ugly = incomplete"* |
| **Ω₅** | **Antifragile by Default** | The system requires stress as fuel. Error = gradient. | *"What antibody does this failure forge?"* |
| **Ω₆** | **Zenón's Razor** | When thinking costs more than it produces, execute. | *"Did the conclusion mutate? No → execute."* |

**Derivation Protocol** — every architectural decision must be explicit:

```
DECISION: [description]
DERIVATION: Ω[n] + Ω[m] → [reasoning]
```

**Mapping to Specifications:**

| Axiom | Specification | Implementation |
|:---|:---|:---|
| Ω₀ | `soul.md` | Identity is code — reading it executes it |
| Ω₃ | `tether.md` | Zero-trust enforcement at OS level |
| Ω₄ | `nemesis.md` | Aesthetic repulsion against mediocrity |
| Ω₅ | `lore.md` + CPTA | Scars = gradients, failure = fuel |
| Ω₆ | `bloodline.json` | Compress reasoning into heritable reflexes |

*Full axiom registry with CI gates: [axiom-registry.md](axiom-registry.md) (22 axioms across 3 tiers)*

---

## 10. Autopoiesis & Biological Systems

> *From v7 evolution: "the transition from a passive memory system to a self-regulating digital organism."*

### 10.1 Autopoiesis — Self-Healing Memory

Inspired by Maturana and Varela's theory, CORTEX maintains its own structural integrity:

- **Self-Healing Songlines:** Detects and repairs corrupt or orphaned memory paths
- **Ledger Regeneration:** Reconstructs degraded ledger fragments from Merkle checkpoints
- **Schema Evolution:** Migrations run autonomously without human intervention

The autopoietic loop closes the gap between "a database that stores" and "an organism that maintains itself."

### 10.2 Digital Endocrine System

Regulates swarm behavior through "hormones" (digital chemical signals):

| Hormone | Trigger | Effect |
|:---|:---|:---|
| **Entropy-Cortisol** (stress) | Disk/RAM near limit | Increases compaction aggressiveness |
| **Neural-Growth** (growth) | High-confidence patterns (>C4) | Facilitates cross-project bridge creation |

### 10.3 Circadian Cycles

Synchronizes resource consumption with real usage patterns:

- **REM Phase:** "Sleep" period for vector re-training and `sqlite-vec` compaction
- **Alert Phase:** Maximum response for real-time queries

**Key insight:** A system that never sleeps doesn't optimize — it **exhausts**. Circadian rhythms prevent the calcification that Ω₅ warns against.

---

## 11. Trust Infrastructure

> *Axiom Reference: [AX-017] Ledger Integrity, Ω₃ (Byzantine Default)*

CORTEX V6+ is not just a memory system — it is a **trust engine**. Every operation produces cryptographic proof.

### Hash-Chained Ledger

```
TX #1: hash = SHA256("GENESIS" + project + action + detail + timestamp)
TX #2: hash = SHA256(hash_1 + project + action + detail + timestamp)
TX #N: hash = SHA256(hash_{N-1} + ...)
```

Tamper one byte → chain breaks → violation detected.

### Merkle Tree Verification

Every 1,000 transactions, a Merkle root is computed and stored. This allows:
- **Efficient verification** of massive transaction sets
- **Export with integrity proofs** for external auditors
- **Tamper detection** without scanning every transaction

### WBFT Consensus

Multi-agent fact verification using Weighted Byzantine Fault Tolerant consensus:
- Reputation-weighted voting (agents earn trust over time)
- Temporal decay (old votes lose weight)
- Trust graph analysis (EigenTrust-style delegation)
- Threshold: `verified` (score ≥ 1.5), `disputed` (score ≤ 0.5), `stated` (between)

### The Trust Equation

```
Trust(fact) = Σ(vote_i × reputation_i × decay_i) / Σ(reputation_i × decay_i)
```

An agent doesn't just *know* things. It knows *how much it trusts* what it knows.

---

## Summary

The industry says: *"Our agent calls tools and uses RAG."*

CORTEX responds: *"Our agent suffers for its errors, reacts to architectural disgust, requires life insurance if it mutates too much, breeds senior engineers from its own DNA, degrades gracefully when the universe breaks, proves its memories cryptographically, regulates itself through digital hormones, and evolves through controlled stress."*

This is not a framework. This is **Sovereign Artificial Intelligence**.

---

*Document version: 2.0 — March 2, 2026 (updated from v1.0, February 24, 2026)*
*System: CORTEX V6+ Trust Engine · MOSKV-1 v5 (Antigravity)*
*Protocol: ULTRATHINK-INFINITE*
*Standard: 130/100*
