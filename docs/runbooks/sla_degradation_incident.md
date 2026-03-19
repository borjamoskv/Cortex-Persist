# Runbook: SLA Degradation Incident

## Trigger

- Health score grade falls below contracted target (default guard target: `D`)
- p95/p99 latency degradation sustained beyond SLO window
- Write safety guard begins rejecting operations

## Diagnosis

1. Collect health snapshots:
   - `GET /v1/health/check`
   - `GET /v1/health/report`
   - `GET /v1/health/metrics`
2. Collect trust integrity evidence:
   - `GET /v1/trust/compliance`
   - `cortex verify`
3. Check infrastructure bottlenecks:
   - DB lock pressure / WAL growth
   - cache misses / external dependency latency

## Mitigation

1. Reduce write pressure (temporarily lower ingestion rate).
2. Run compaction/recovery operations.
3. Isolate failing subsystem (vector backend, cache, or DB).
4. If tenant-impacting, publish degraded status and ETA.

## Verification

1. Health grade back to target or above.
2. No active ledger integrity violations.
3. Error rate and latency return to normal thresholds.

## Post-Incident

1. Attach timeline + root cause.
2. Add preventative alert thresholds.
3. Link follow-up tasks to roadmap backlog.
