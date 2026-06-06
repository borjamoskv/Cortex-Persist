# CORTEX RUNTIME LOOP v1: THE EXECUTION HEART

> **Reality Level:** `C5-REAL` (Executable Infrastructure Spec)
> **Aesthetic:** `Industrial Noir 2026`
> **Definition:** CORTEX Runtime Loop is a continuous event ingestion, deterministic execution, and financially metered causality engine operating as a closed computational system.

## 1. CORE LOOP PRINCIPLE
**The system is not executed. It is continuously replayed forward.**
There is no "start/stop". There is only:
* ingest
* validate
* execute
* persist
* bill

## 2. RUNTIME PIPELINE (REAL FLOW)
```text
Event Ingestion
    ↓
Determinism Guard
    ↓
Causal Ordering Engine
    ↓
Execution Sandbox
    ↓
State Derivation
    ↓
Ledger Append (hash-chained)
    ↓
Snapshot Manager
    ↓
Billing Emission (SSU)
    ↓
Observability Stream
    ↺ LOOP
```

## 3. RUNTIME DAEMONS

### 3.1 Ingestion Daemon
Listens to all agent actions, tool calls, and memory writes.
```python
while True:
    event = listen()
    validated = validate(event)
    enqueue(validated)
```

### 3.2 Execution Worker Pool
The muscle. Pulls from the queue, orders causally, executes deterministically, and appends to the ledger.
```python
def worker(event_queue):
    while True:
        event = event_queue.pop()
        ordered = causal_order(event)
        result = execute(ordered)
        ledger.append(result)
```

### 3.3 Replay Service (Live + Historical)
This is not a debug tool. It is the **second runtime mode**.
```python
def replay_range(a, b):
    events = ledger.slice(a, b)
    state = {}
    for e in order(events):
        state = execute(e)
    return state
```

### 3.4 Billing Emitter (SSU Engine)
Every execution generates economy dynamically.
```python
def bill(event):
    units = compute_SSU(event)
    emit_invoice_line(user=event.agent_id, units=units)
```

## 4. SYSTEM STATE IS A SIDE EFFECT
**Crucial Architectural Shift:**
State is not saved as primary truth. State is exclusively a derivation of the loop.
`Ledger → Replay → State Projection`

## 5. FAILURE IS A FIRST-CLASS STREAM
Failure is no longer an error log; it is a billable insight stream mapping entropy and divergence.
```python
def monitor():
    if divergence_detected():
        emit_failure_event()
        adjust_pricing_multiplier()
```

## 6. HARD GUARANTEES (C5-REAL ENFORCEMENT)
The runtime loop aggressively imposes:
* No global clock.
* No nondeterministic RNG.
* No external I/O without a strict hash commit.
* No execution outside the determinism sandbox.
