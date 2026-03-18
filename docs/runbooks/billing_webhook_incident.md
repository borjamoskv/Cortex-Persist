# Runbook: Billing Webhook Incident

## Trigger

- Stripe webhook endpoint starts returning `>=500`
- New subscriptions are paid but API keys are not provisioned
- Cancellations are paid/refunded but keys remain active

## Immediate Actions

1. Confirm API health and billing route registration:
   - `GET /health`
   - Verify Stripe routes are enabled (`STRIPE_SECRET_KEY` set).
2. Check webhook signature configuration:
   - `STRIPE_WEBHOOK_SECRET`
3. Inspect logs around `/v1/stripe/webhook` for signature or payload errors.

## Containment

1. If provisioning is delayed, pause outbound customer comms and mark status as degraded.
2. Reprocess affected events from Stripe dashboard (manual replay).
3. For cancellations, manually revoke affected keys via admin tooling.

## Verification

1. Execute one test checkout in Stripe test mode.
2. Confirm API key provisioning and tenant scoping.
3. Confirm usage endpoint visibility for the tenant (`/v1/usage`).

## Post-Incident

1. Record impacted tenant ids and event ids.
2. Document MTTR and root cause.
3. Add regression test if failure mode was code-path specific.
