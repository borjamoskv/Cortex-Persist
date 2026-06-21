# CORTEX PERSIST: 30-DAY MVP & GTM PIPELINE

**Goal:** Close the first 3 paying Enterprise/Scale-up customers within 30 days.

## 1. The MVP Scope (Strictly scoped, zero fluff)

To sell the vision of the "AI Execution Control Plane", the MVP must flawlessly demonstrate the **Deterministic Replay Layer** and **Inline Policy Enforcement**.

### Component 1: Cortex Trace (The Wedge)
- **Feature:** Python SDK (`pip install cortex-persist`) that wraps OpenAI/Anthropic SDKs automatically.
- **Output:** Captures inputs, outputs, latency, token usage, and tool calls into a local SQLite/Postgres DB.
- **UI:** A simple, fast web dashboard (FastAPI + React/Tailwind) to view the spans and traces.
- **Killer Action:** A "Replay" button on the UI that re-runs the exact trace state in a sandbox.

### Component 2: Cortex Guard (The Security Hook)
- **Feature:** A synchronous middleware that intercepts the LLM output before returning it to the user.
- **Rule 1:** Regex-based PII redaction (Emails, SSN, Credit Cards).
- **Rule 2:** Strict JSON schema enforcement (rejects/retries if LLM breaks schema).
- **Value:** The demo shows an LLM trying to leak an email, and Cortex Guard returning `[REDACTED]`.

### Component 3: Cortex Eval (The Expansion)
- **Feature:** Ability to tag a trace in the UI as a "Golden Test Case".
- **Execution:** A simple CLI command `cortex eval run` that runs all golden cases against a new prompt version and outputs a pass/fail diff.

---

## 2. The 30-Day Go-To-Market Execution

### Week 1: Build & Polish the Wedge
- Strip out all internal experimental architecture from the public-facing API.
- Create a flawless 5-minute onboarding experience:
  ```python
  import cortex
  cortex.init(api_key="...", project="customer-support-bot")
  # Everything else is auto-instrumented
  ```
- Record a 2-minute Loom video demonstrating: Bug happens -> Find in Cortex Trace -> Fix prompt -> Run Cortex Eval -> Deploy.

### Week 2: Targeted Outreach (The ICP)
- **Target:** Lead Engineers, Platform Engineers, and Head of AI at Series B+ B2B SaaS companies.
- **Message:** *"Hey [Name], noticed you're deploying LLM agents. How are you handling non-deterministic failures in production? We built a drop-in deterministic replay and guardrail layer. Takes 10 mins to install. Can I show you a 2-min demo?"*
- **Channel:** LinkedIn direct outreach and targeted Twitter DMs to AI engineers.

### Week 3: Demos & Security Hook
- Conduct 10-15 demos.
- **Demo Flow:**
  1. Show how LangChain/custom code is a black box.
  2. Drop in Cortex.
  3. Show the dashboard trace.
  4. **The Kill Shot:** Trigger a policy violation and show Cortex Guard blocking it inline. Say: *"This is how you pass SOC2 with LLMs."*
- Offer a 14-day free pilot on their dev/staging environment.

### Week 4: Conversion & Pricing
- Convert 3 successful pilots into paid contracts.
- Anchor pricing at $500 - $1,000/month for early adopters (discounted from "Enterprise" tiers) in exchange for case studies.

---

## 3. What We Are NOT Building in 30 Days
- Complex multi-agent visualization.
- Custom LLM-as-a-judge models (use standard GPT-4 as the judge for now).
- Complex cloud Kubernetes deployments (offer managed SaaS or simple Docker compose for self-hosting).
- "Thermodynamic optimization" (Keep this as internal IP for system efficiency, do not expose to the user).
