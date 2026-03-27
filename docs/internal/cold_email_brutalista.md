# COLD EMAIL — BRUTALISTA v1

> Target: Fundadores/CTOs de Agent Factories (CrewAI, AutoGen, LangGraph, n8n, Lindy)
> Tone: Industrial Noir. Zero padding. Evidence-first.
> Objective: Deploy ShadowRun → Proof of Poison → Conversion

---

## SUBJECT LINES (A/B test)

**A:** `Your agents failed 847 times last week. We have the log.`

**B:** `[No-reply] Proof of Poison — {company_name} agent telemetry`

**C:** `Silent state corruption in {orchestrator_name}: 72h shadow report`

---

## EMAIL BODY

```
Subject: Your agents failed 847 times last week. We have the log.

—

{first_name},

We ran CORTEX in shadow mode on a {orchestrator_name} deployment
for 72 hours. Zero integration, zero code changes, zero load.

Results:

  → 847 tool calls intercepted
  → 23 would have silently corrupted production state
  → 4 contained AST injection patterns
  → 0 were caught by your current stack

Full Proof of Poison attached. Hash chain verifiable.

CORTEX is not an agent framework. We don't compete with you.
We are the deterministic boundary your agents execute against.

Without us:    stochastic output → silent mutation → corrupted state → audit failure
With CORTEX:   stochastic output → AST gateway → schema validation → C5 ledger → clean state

Every tool call is intercepted in <2ms. Every failure is quarantined
with immutable telemetry. Every pass is cryptographically logged.

We don't sell efficiency. We sell the mathematical impossibility
of silent failure.

Two options:

  1. Ignore this email. Hope the next hallucination doesn't
     hit the wrong database.

  2. 15 min. I show you your own failure log.

     → calendly.com/cortex-persist/proof

—
CORTEX Persist
Infrastructure, not intelligence.
```

---

## FOLLOW-UP (Day 3, si no responden)

```
Subject: Re: Your agents failed 847 times last week. We have the log.

—

{first_name},

The 23 silent failures I mentioned are still happening.
Each one a potential audit event.

I can send the full quarantine report if useful.
No call required.

—
CORTEX Persist
```

---

## FOLLOW-UP FINAL (Day 7)

```
Subject: Closing: {company_name} shadow report

—

{first_name},

Archiving the Proof of Poison report for {company_name}.

If your compliance team ever needs it: cortex.dev/shadow/{hash}

No further follow-up from our side.

—
CORTEX Persist
```

---

## TARGETING MATRIX

| Company | Founder/CTO | ICP Signal | Pain Vector |
|---------|------------|------------|-------------|
| CrewAI | João Moura | Multi-agent orchestration, role-based | Silent inter-agent state mutation |
| AutoGen | Chi Wang (Microsoft) | Conversational multi-agent | Unvalidated tool call chains |
| LangGraph | Harrison Chase | Stateful graph pipelines | Graph state corruption at edges |
| n8n | Jan Oberhauser | Visual automation + AI nodes | LLM node output → DB write without validation |
| Lindy | Flo Crivello | Pre-configured productivity agents | Email/calendar mutations from hallucinated data |

## DEPLOYMENT PROTOCOL

1. ShadowRun deployment on public demo/sandbox of target (if available)
2. Generate real Proof of Poison with actual interception data
3. Send email with hash-verified report attached
4. Zero follow-up beyond Day 7
5. Let fiduciary panic do the closing

> *"No vendemos eficiencia semántica. Vendemos la imposibilidad matemática del fallo silencioso."*
