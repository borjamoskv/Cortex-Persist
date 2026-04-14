# cortexpersist.com — Landing Page Copy

> Home copy lista para pegar en cortexpersist.com.
> El orden correcto arriba del fold es: 1. hero, 2. proof strip de 3 bloques, 3. problema, 4. solución, 5. demo, 6. features, 7. use cases, 8. technical credibility, 9. CTA final.

---

## 1. Hero

**Verifiable memory for teams shipping high-stakes AI workflows**

Verifiable memory, tamper-evident lineage, and exportable evidence for AI systems that need more than a prompt window.

[Get Started] [View Demo]

*(Edge variant más agresiva:)*
> **Your AI can act. Now make it accountable.**
> Persistent memory, tamper-evident lineage, and exportable evidence for systems that cannot afford amnesia.

---

## 2. Proof strip

**Verifiable memory**
Preserve workflow context and decisions in an inspectable form teams can review later.

**Tamper-evident lineage**
Detect whether a decision record changed instead of reconstructing it from traces and guesswork.

**Exportable evidence**
Package decision records into artifacts teams can share for reviews, incident response, and audits.

---

## 3. Problem

**Most AI systems can generate output. Few can justify their history.**

Agents are getting better at acting, calling tools, and producing plausible responses.
What they still lack is durable operational memory with evidence.

Without that layer, systems drift, repeat work, lose context, and leave weak audit trails.

You do not have memory.
You have fragments, logs, and optimism.

---

## 4. Solution

**CORTEX-Persist makes the decision record verifiable**

CORTEX-Persist is a local-first memory and verification substrate for AI systems that need to preserve, verify, and export what happened.

It combines:
- structured memory
- tamper-evident ledgering
- hybrid retrieval
- memory lifecycle governance
- exportable evidence

So your stack can do more than continue text.
It can leave behind a decision record teams can inspect under pressure.

---

## 5. Demo section

**From event to evidence in under a minute**

**1. Store memory**
```bash
cortex store procurement "Vendor X failed compliance check" \
  --type decision \
  --confidence C4 \
  --source agent:reviewer
```

**2. Generate lineage**
Each write can be chained into a tamper-evident ledger with transaction ID, timestamp, hash, and previous hash.

**3. Retrieve context**
```bash
cortex search "compliance vendor failure"
```

**4. Verify integrity**
```bash
cortex ledger verify
```

Result: persistent memory with searchable context and verifiable history.

[Run the Demo] [Read the Docs]

---

## 6. Feature grid

**Built for memory that has to survive contact with reality**

**Structured Memory**
Store facts, decisions, discoveries, and errors as typed units with metadata, confidence, and temporal validity.

**Tamper-Evident Ledger**
Attach cryptographic lineage to memory operations so decision history is not left to interpretation.

**Hybrid Retrieval**
Combine semantic and lexical retrieval for context that is actually reusable in live systems.

**Memory Governance**
Promote, compact, decay, archive, or discard memory instead of turning context into a permanent landfill.

**Local-First Runtime**
Start with SQLite and sqlite-vec locally. Extend to cloud backends when scale or deployment needs change.

**Audit-Ready History**
Support internal review, compliance workflows, and postmortems with evidence instead of reconstruction theater.

---

## 7. Use cases

**Where CORTEX-Persist hits hardest**

**AI agents with tools**
Keep reliable context across steps, sessions, and agent boundaries.

**Long-running automation**
Reduce repetition, drift, and memory loss in workflows that operate over time.

**Compliance and audit**
Maintain verifiable operational history for regulated or review-heavy environments.

**Decision systems**
Track not only the output, but the lineage behind how a system arrived there.

---

## 8. Why not just use a vector database?

**Because similarity is not lineage**

A vector database can retrieve related text.
It does not tell you what was stored, when it changed, how it was derived, or whether the history was tampered with.

CORTEX-Persist adds the missing layers:
- typed memory
- temporal validity
- confidence levels
- cryptographic lineage
- governed lifecycle
- auditability

Memory without integrity is just plausible storage.

---

## 9. Technical credibility

**Built for real systems, not benchmark cosplay**
- Python-first architecture
- SQLite and sqlite-vec by default
- optional cloud extensions
- encryption at rest
- async-friendly design
- CLI and API surfaces
- typed package support
- memory lifecycle controls

This is infrastructure for systems that operate repeatedly, not a one-shot prompt wrapper.

---

## 10. CTA block

**Make your AI stack remember with evidence**

Start with persistent memory.
Add lineage when memory starts to matter.
Keep both when accountability becomes non-negotiable.

[Get Started] [View Demo] [GitHub]

---

## Extras

**Microcopy & Navigation**
- Nav: Product, Demo, Docs, GitHub, Security
- CTA variants: Get Started, View Demo, Read the Docs, Explore GitHub, Verify the Ledger
- Footer one-liner: Persistent memory for AI systems that need evidence, not vibes.

**GitHub Integration Strings**
- **Description:** Verifiable memory and decision lineage for high-stakes AI workflows.
- **README Opening:** CORTEX-Persist gives teams shipping AI into high-stakes workflows verifiable memory, tamper-evident decision lineage, and exportable evidence.

---
**Notas de implementación:** No metas termodinámica, Ω ni doctrina en el primer scroll. Eso va en una página aparte tipo *Architecture / Principles / Why CORTEX*.
