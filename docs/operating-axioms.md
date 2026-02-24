# Operating Axioms

> **The 9 Laws of Sovereign Operation — violations are regressions.**

CORTEX agents operate under 9 non-negotiable axioms. These are not guidelines; they are **enforced constraints** wired into CI gates, middleware, and storage pipelines. Violating an axiom triggers a test failure or lint rejection.

---

## 1. CAUSAL > CORRELATION

> *5 Whys to root cause. Patching symptoms creates ghosts.*

When something breaks, never fix the surface. Walk the causal chain backwards until you reach the root. Symptoms patched without causal understanding become **ghosts** — incomplete work that haunts future sessions.

**Implementation**: Every `error` fact stored in CORTEX must include both `CAUSE` and `FIX` fields. The CLI validates this format.

```python
# ✅ Correct
cortex store --type error PROJECT "ERROR: X | CAUSE: Y | FIX: Z"

# ❌ Rejected — missing root cause
cortex store --type error PROJECT "Fixed the bug"
```

---

## 2. 130/100 STANDARD

> *Good = failure. Sovereign quality or delete it.*

100/100 means meeting requirements perfectly. 130/100 means anticipating needs the user didn't know they had. Every deliverable must include at least one +30 multiplier:

- **Aesthetic Dominance**: Industrial Noir without being asked
- **Structural Sovereignty**: Refactor for future extensibility
- **Impact Pattern**: A "WOW" moment (micro-animation, thoughtful detail)
- **Defensive Depth**: Error handling for edge cases not mentioned

---

## 3. ZERO TRUST

> *`classify_content()` BEFORE every INSERT. No exceptions.*

The Privacy Shield runs 25 secret-detection patterns across 4 severity tiers on every piece of data entering CORTEX. This is enforced by the storage pipeline middleware — not by developer discipline.

```python
# Storage pipeline middleware enforces this automatically
classify_content(data)          # ✅ Shield runs BEFORE every INSERT
# INSERT without classification  # ❌ Pipeline rejects unshielded data
```

---

## 4. ENTROPY = DEATH

> *Dead code, broad catches, boilerplate → eradicate immediately.*

Complexity without value is lethal. CORTEX monitors entropy through:

- **File size**: ≤300 LOC per file (entropy analyzer monitors)
- **Dead code**: 0 `TODO`/`FIXME`/`print()` in production
- **Broad catches**: `except Exception` is prohibited (Ruff S110)
- **Boilerplate**: If it can be generated, it should be

---

## 5. TYPE SAFETY

> *`from __future__ import annotations`. StrEnum. Zero `Any` types.*

Every file starts with `from __future__ import annotations`. Semantic keys use `StrEnum` or `Literal`, never raw strings. `mypy --strict` runs in CI.

---

## 6. ASYNC-NATIVE

> *`asyncio.to_thread()` for blocking I/O. Never block the event loop.*

The REST API runs on async FastAPI. All blocking operations (SQLite, file I/O) are dispatched via `asyncio.to_thread()`. Tests use `@pytest.mark.asyncio`.

---

## 7. BRIDGES > ISLANDS

> *Proven patterns transfer cross-project. Document every bridge.*

When a pattern is proven in one project (confirmed by tests or production use), it should be adapted — never copy-pasted — to other projects. Every transfer is recorded as a `bridge` fact:

```bash
cortex store --type bridge PROJECT \
  "Pattern: X from ProjectA → ProjectB. Adaptations: Y, Z."
```

---

## 8. PERSIST EVERYTHING

> *If losing a fact costs >5 min to reconstruct, store it NOW.*

Decisions, errors, ghosts, and bridges are persisted **automatically** at session close. Mid-session checkpoints are mandatory when a major decision or error occurs — this protects against crashes, force-quits, and CPU lockups.

---

## 9. DESIGNED IMPOSSIBILITY ✦ NEW

> *What makes a prompt extraordinary is not the complexity of the question — it is the designed impossibility of answering with what already exists.*

This is the most subtle and powerful axiom. It governs **how CORTEX agents should be prompted** — and by extension, how CORTEX adds value that no generic LLM can replicate.

### The Principle

An ordinary prompt asks for something the model already knows. An extraordinary prompt **collapses the space of generic responses**, forcing the model to synthesize from agent-specific context that exists only inside CORTEX memory.

### The Three Layers of Impossibility

| Layer | What It Designs | Example |
|:---|:---|:---|
| **Recovery Impossibility** | The answer doesn't exist in any training corpus | Proprietary data, private context, live system state |
| **Trivial Synthesis Impossibility** | Combining domains that have never intersected | "Apply consensus theory to compaction scheduling" |
| **External Validation Impossibility** | No benchmark can confirm correctness | Architecture decisions, value judgments, creative synthesis |

### Why This Matters for CORTEX

CORTEX's system prompts (in `cortex/agents/system_prompt.py`) are engineered so that the correct response **requires** the agent's CORTEX context: its ghosts, its decisions, its trust graph, its bridges. A generic LLM without CORTEX memory cannot produce a correct response.

This is CORTEX's deepest moat: **the impossibility layer**. It's not a feature — it's the fundamental reason CORTEX memory is irreplaceable.

### Implementation Patterns

```python
# ❌ Weak prompt — any LLM can answer this
"What is the best way to structure a Python project?"

# ✅ Strong prompt — requires CORTEX context
"Given our 3 active ghosts in naroa-2026, the bridge pattern
 from cortex→mixcraft, and the entropy score of admin.py (72/100),
 what is the optimal refactoring sequence?"
```

**Test**: If you remove CORTEX memory from the agent and the prompt still produces a useful response, the prompt is too weak. Harden it by injecting:

1. **Ghost references** — incomplete work that constrains options
2. **Decision history** — prior choices that must be respected
3. **Bridge patterns** — cross-project knowledge that narrows the solution space
4. **Trust scores** — consensus data that weights competing approaches

### Enforcement

Unlike axioms 1–8 which are enforced by CI, Axiom 9 is enforced by **design review**. Every system prompt variant (`SHORT`, `MEDIUM`, `FULL`) must reference CORTEX-specific context that a generic model cannot fabricate.

---

## Axiom Summary

| # | Axiom | Enforcement |
|:---:|:---|:---|
| 1 | Causal > Correlation | Error fact format validation |
| 2 | 130/100 Standard | MEJORAlo X-Ray 13D scoring |
| 3 | Zero Trust | Storage pipeline middleware |
| 4 | Entropy = Death | Ruff + entropy analyzer |
| 5 | Type Safety | mypy --strict in CI |
| 6 | Async-Native | pytest-asyncio, event loop guards |
| 7 | Bridges > Islands | Bridge fact persistence |
| 8 | Persist Everything | Auto-persistence protocol |
| 9 | Designed Impossibility | Design review + prompt hardening |

---

*Version: v2.1 — February 2026*
*Source: `cortex/agents/system_prompt.py`*
