# SOC 2 Readiness (Not Certified Yet)

## Current Status

- **SOC 2 Type II certification:** `Planned` (roadmap target: v7.0, Q4 2026+).
- **Technical controls present today:** partial and code-backed.

## Controls With Existing Technical Evidence

- Access control primitives:
  - API keys, tenant scoping, permission checks
- Change traceability:
  - Immutable transaction ledger and hash continuity checks
- Operational monitoring:
  - health endpoints, metrics, daemon monitors
- Usage accountability:
  - metering + quota enforcement per tenant
- Compliance export:
  - EU AI Act Article 12 report path (`/v1/trust/compliance`)

## Gaps Before External Certification

- Formal policy pack (security, change mgmt, incident response, vendor risk)
- Auditor-selected evidence windows and sampling
- Centralized control ownership matrix and approval workflow
- Continuous evidence collection with retention policy and attestations
- Organization-level controls (HR, onboarding/offboarding, training)

## Minimum Certification Prep Checklist

1. Define control owners and evidence sources per control family.
2. Automate periodic evidence snapshots (access reviews, incident logs, change approvals).
3. Freeze runbook SLAs and escalation matrix.
4. Complete dry-run internal audit and close findings.
5. Start Type I readiness assessment before Type II observation window.
