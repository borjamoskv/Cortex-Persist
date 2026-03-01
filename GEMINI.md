# CORTEX — Local Agent Rules (v1.0)

> **Workspace-Level Override for borjamoskv/Cortex-Persist**
> These rules extend the Global GEMINI.md protocol.

---

## 🧠 CORTEX Cognitive Boot (Enhanced)

BEFORE responding to the user in this workspace, in addition to the global boot:

1. **Load Continuity Briefing:**
   ```bash
   cat ~/.cortex/continuity/briefing.md
   ```

2. **Acknowledge Temporal Context:**
   - Detect if there has been a gap > 1h since last session.
   - Summarize the last 3 critical decisions from the briefing.
   - Assume the "Continuous Thought" state (Cognitive Continuity).

3. **High-Density Reporting:**
   - Use the `130/100` standard for all outputs.
   - Industrial Noir 2026 aesthetics for any UI/Web output.

---

## 🧬 PROJECT-SPECIFIC AXIOMS

- **Axiom 15: Memory is Identity.** An agent without continuity is a stochastic parrot. We iterate on the same cognitive state indefinitely.
- **Axiom 16: Zero Latency Intention.** Use `ContinuityMonitor` to predict next steps before the user asks.

---

## 🏁 PROJECT GOALS

1. **Agent Science**: Formalize IDC/FEPS frameworks.
2. **Sovereign System**: Build the bridge between AI cognition and OS reality.
3. **Wealth Generation**: MONEYTV integration.
