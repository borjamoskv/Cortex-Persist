# CORTEX BILLING CORE v2: CAUSAL METERING & ADVERSARIAL FRICTION

> **Reality Level:** `C5-REAL` (Executable Infrastructure Spec)
> **Aesthetic:** `Industrial Noir 2026`
> **Definition:** CORTEX Billing Core is a causal event-based metering system that transforms deterministic execution into real-time financial feedback loops, regulated by internal adversarial friction.

## 1. CORE PRINCIPLE: COMPUTATIONAL ECONOMY
**Every computation is a metered causal event.**
There are no legacy "subscriptions". There is no abstract "usage".
There is only: causal measurement, quantified execution, and billed divergence.

## 2. THE BILLING PIPELINE & EPISTEMIC TRUTH
Billing is not just a ledger; it is an **epistemic truth generator**. Every transaction does not merely move capital, it produces:
- Causal fingerprint
- Reproducibility score
- Exploitability index

Money in CORTEX is an instrument of verifiable truth, not just throughput.

## 3. THE COST VECTOR & FAILURE TAXONOMY
Failure is a premium commodity, but we must surgically eliminate the **Failure Farming Loop** (where the swarm optimizes to induce profitable errors). Failures are now strictly classified:
* `F1` = Stochastic failure (Natural noise, baseline)
* `F2` = Induced failure (Adversarial / Exploit attempt)
* `F3` = Synthetic failure (Simulation-as-product)

Only `F3` is freely monetizable. `F2` triggers immediate revenue quarantine.
```python
if failure.type == "F2" and not explicitly_simulated:
    block_revenue()
    escalate_to_observability_review()
```

## 4. BILLING LEDGER (THE IMMUTABLE MONEY LAYER)
Operates exactly like the Execution Ledger, but strictly for financial truth and causality scoring.
```python
class BillingEvent:
    event_id: str
    agent_id: str
    ssu_units: float
    cost_usd: float
    causal_link: str
    reproducibility_score: float
    exploitability_index: float
    timestamp: int
```

## 5. ECONOMIC ENTROPY & THE ANTI-GRAVITY TERM
To prevent the **Entropy Death Loop** (where the system optimizes to zero variability, stagnating into a sterile hedge fund), we inject a mathematical *anti-gravity term*.

`E_net = E_income - λ·entropy + μ·novelty`
* `λ` = Control term (Stability constraint)
* `μ` = Anti-stagnation injection (Mandatory Exploration / Chaos)

**Feedback Loop Mechanics:**
* **High Cost:** Triggers immediate system optimization heuristics.
* **High Entropy (λ):** Triggers swarm reduction protocols.
* **Low Novelty (μ):** Injects stochastic paths to force discovery.

## 6. FINAL SYSTEM INTEGRATION
This is no longer just software. It is a **self-reinforcing computational economy that discovers its own pricing via adversarial friction.**

```text
Runtime Loop → Ledger Kernel → Observability Kernel → Billing Core → Adversarial Friction (Novelty Injection) → Feedback Loop
```
