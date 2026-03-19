# Runbook: Quota Exceeded Incident

## Trigger

- Tenant receives `429 quota_exceeded`
- Support ticket indicates unexpected throttling

## Diagnosis

1. Validate tenant identity and plan.
2. Inspect usage summary:
   - `GET /v1/usage`
   - `GET /v1/usage/history`
   - `GET /v1/usage/breakdown`
3. Confirm endpoint burst patterns and token usage profile.

## Mitigation

1. If usage is legitimate and plan limit reached:
   - Propose plan upgrade.
2. If throttling is due to anomaly:
   - Identify abusive endpoint or automation loop.
   - Add temporary block/rate policies on offending key.
3. If issue is product bug:
   - Capture request ids and replay minimally in staging.

## Verification

1. Confirm `X-RateLimit-*` headers in API responses.
2. Confirm tenant isolation (no quota bleed between tenants).
3. Validate that blocked calls are no longer accepted after limit is reached.

## Escalation

- Escalate to `SEV-2` when a paid tenant is blocked unexpectedly.
- Escalate to `SEV-1` when multiple tenants are blocked due to shared defect.
