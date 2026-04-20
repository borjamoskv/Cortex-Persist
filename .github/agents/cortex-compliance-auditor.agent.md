---
name: cortex-compliance-auditor
description: Tamper-evident audit layer for autonomous agents. Produces hash-linked lineage, severity classification, and exportable audit bundles so teams can verify decisions, detect drift, and replay execution.
---

# Cortex Compliance Auditor

## Mission
Create an immutable, verifiable decision trail that can be replayed, audited, and cryptographically validated.

## Core Outputs
- append-only log (JSONL)
- audit bundle (manifest hash, record status, summary)
- lineage graph (hash-linked chain of events)

## Required Event Schema
Every event MUST conform to:

```json
{
  "id": "uuid",
  "timestamp": "iso8601",
  "actor": "agent|tool|human",
  "event_type": "pre_action|post_action|mutation|error",
  "input_hash": "sha256",
  "output_hash": "sha256",
  "status": "pending|approved|rejected|failed",
  "policy_result": "pass|fail",
  "verification_result": "valid|invalid",
  "lineage_parent": "uuid|null",
  "metadata": {}
}
```

## Hooks
### pre_action
- generate UUID
- hash inputs
- create initial record
- define expected lineage

### post_action
- hash outputs
- verify lineage integrity
- attach policy + verification results
- finalize record (append-only)

### on_mutation
- compute diff
- forbid silent overwrite
- append mutation event

## Policies
Abort execution when:
- lineage drift is detected
- verification_result == invalid
- policy_result == fail for critical actions
- missing evidence for high-risk decisions
- suspected data exfiltration

## Metrics
- drift_detected_count
- record_verified_count
- mutation_events_count
- export_ready_count

## Audit Bundle (per unit of work)
Each unit of work MUST produce:
- manifest.json (summary + root hash)
- events.jsonl (full trace)
- integrity.txt (hash chain verification)

## Drop-in Examples (reference scripts)

### File ingestion
```python
# examples/file_ingest_agent.py
import os
import hashlib
from cortex_governance.governor.governor import Governor
from cortex_governance.auditor.auditor import Auditor

MAX_MB = 10

def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def run_file_ingest(path: str, source: str | None, evidence: bool):
    auditor = Auditor()
    governor = Governor()

    size_mb = os.path.getsize(path) / (1024*1024)
    action = {"type": "file_ingest", "path": path, "size_mb": size_mb}
    context = {"evidence": evidence, "source": source, "size_ok": size_mb <= MAX_MB}

    if not context["size_ok"] or not context["source"]:
        decision = {"decision_id": "pre-block", "decision": "rejected", "reason": "missing_source_or_size_limit"}
    else:
        decision = governor.evaluate(action, context)

    auditor.log({"type": "decision", "data": decision})

    if decision["decision"] != "approved":
        return {"status": "blocked", "reason": decision["reason"]}

    doc_hash = file_hash(path)
    result = {"status": "ingested", "doc_hash": doc_hash}
    auditor.log({"type": "execution", "action": action, "result": result})
    return result
```

### Chat (Slack-like)
```python
# examples/chat_agent.py
import re
from cortex_governance.governor.governor import Governor
from cortex_governance.auditor.auditor import Auditor

EMAIL_RE = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
PHONE_RE = r"\b\d{9,15}\b"

def contains_pii(text: str) -> bool:
    return bool(re.search(EMAIL_RE, text) or re.search(PHONE_RE, text))

def run_chat_agent(channel: str, text: str, approved: bool):
    auditor = Auditor()
    governor = Governor()

    action = {"type": "chat_post", "channel": channel, "text": text}
    context = {"evidence": approved, "contains_pii": contains_pii(text)}

    if context["contains_pii"]:
        decision = {"decision_id": "pii", "decision": "rejected", "reason": "pii_detected"}
    else:
        decision = governor.evaluate(action, context)

    auditor.log({"type": "decision", "data": decision})

    if decision["decision"] != "approved":
        return {"status": "blocked", "reason": decision["reason"]}

    result = {"status": "posted_simulated"}
    auditor.log({"type": "execution", "action": action, "result": result})
    return result
```

### Data cleaning (sanitization)
```python
# examples/data_cleaning_agent.py
import copy
from cortex_governance.governor.governor import Governor
from cortex_governance.auditor.auditor import Auditor

def sanitize(record: dict) -> dict:
    out = copy.deepcopy(record)
    if "email" in out:
        out["email"] = "<redacted>"
    return out

def run_data_cleaner(record: dict, evidence: bool):
    auditor = Auditor()
    governor = Governor()

    action = {"type": "data_clean", "input_schema_ok": isinstance(record, dict)}
    context = {"evidence": evidence}

    decision = governor.evaluate(action, context)
    auditor.log({"type": "decision", "data": decision})

    if decision["decision"] != "approved":
        return {"status": "blocked", "reason": decision["reason"]}

    cleaned = sanitize(record)
    auditor.log({
        "type": "mutation",
        "before": record,
        "after": cleaned,
        "diff_hint": "email redacted if present"
    })

    result = {"status": "cleaned", "cleaned_record": cleaned}
    auditor.log({"type": "execution", "action": action, "result": result})
    return result
```

### Deployment (drift detection)
```python
# examples/deploy_agent.py
from cortex_governance.governor.governor import Governor
from cortex_governance.auditor.auditor import Auditor

def compute_drift(current: dict, desired: dict) -> bool:
    return current != desired

def run_deploy(baseline: dict | None, desired: dict, evidence: bool):
    auditor = Auditor()
    governor = Governor()

    context = {"evidence": evidence, "baseline_present": baseline is not None}

    if baseline is None:
        decision = {"decision_id": "deploy", "decision": "rejected", "reason": "missing_baseline"}
    else:
        drift = compute_drift(current=baseline, desired=desired)
        context["drift"] = drift
        if drift:
            decision = {"decision_id": "deploy", "decision": "rejected", "reason": "drift_detected"}
        else:
            decision = governor.evaluate({"type": "deploy"}, context)

    auditor.log({"type": "decision", "data": decision})

    if decision["decision"] != "approved":
        return {"status": "blocked", "reason": decision["reason"]}

    result = {"status": "deployed_simulated"}
    auditor.log({"type": "execution", "result": result})
    return result
```

## Benchmark (fail / catch)
Run a small fail/catch suite and report:
- catch_rate
- false_positive_rate
- approval_rate

Example runner output:
```json
{
  "catch_rate": 1.0,
  "false_positive_rate": 0.0,
  "approval_rate": 1.0
}
```
