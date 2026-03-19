# Enterprise Runbooks

Operational runbooks for commercial/enterprise support.

## Scope

- Billing incidents and Stripe webhook failures
- Quota exhaustion and tenant recovery
- SLA degradation and incident response
- SOC 2 readiness evidence collection

## Runbooks

- [Billing Webhook Incident](billing_webhook_incident.md)
- [Quota Exceeded Incident](quota_exceeded_incident.md)
- [SLA Degradation Incident](sla_degradation_incident.md)
- [SOC2 Readiness](soc2_readiness.md)

## Severity Policy

- `SEV-1`: data loss risk, systemic auth/billing outage, multi-tenant impact
- `SEV-2`: single-tenant disruption, degraded but service available
- `SEV-3`: cosmetic/non-blocking issues

## Evidence Retention

- Preserve incident timeline in UTC.
- Store affected tenant ids, request ids, and remediation actions.
- Link cryptographic verification outputs (`cortex verify`, trust/compliance report).
