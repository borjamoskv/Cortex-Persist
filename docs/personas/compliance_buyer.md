# What Artifact Do I Receive?

As a Compliance Officer, Legal Counsel, or Buyer of trust infrastructure, you need to know exactly what Evidence CORTEX provides when an AI agent makes a disputed decision.

## The Problem
When regulators or internal auditors ask "Why did the autonomous system deny this loan?" or "Why was this PII deleted?", traditional observability platforms (Datadog, Splunk) provide unstructured text logs that can be edited by an admin or manipulated post-hoc. 

*Logs are not Evidence.*

## The CORTEX Solution
CORTEX provides a **Mathematically Proven Audit Pack** per incident or decision.

Here is the exact artifact that is delivered to your inbox, ready for presentation to EU AI Act compliance boards or external auditors:

> **View Live Artifact:** [Download `examples/audit_proof_artifact.json`](../examples/audit_proof_artifact.json)

## Why This Satisfies The Law

According to `EU AI Act Article 12`, high-risk systems must have automatic recording of events (logging) to ensure traceability of operations throughout their lifecycle. 

CORTEX goes beyond mere logging by employing **Hash-Chaining** and **Merkle Roots**.
1. **Hash-Chaining:** If anyone tries to modify the JSON artifact above after the fact to cover up a mistake, the `current_hash` won't match the database signature.
2. **Merkle Roots:** We periodically seal thousands of these decisions into a single global cryptographic footprint.

When you buy CORTEX, you are buying the ability to hand an auditor a command (`cortex verify record X`) and an immutable JSON receipt that proves beyond doubt what the AI knew at the time of execution.
