# Deployment Hardening

This document covers hardening for the source-installed local-first runtime, plus beta guidance for self-hosted API deployments.

## Current Reality

The most mature deployment path today is:

- a single-node source install
- a small self-hosted deployment if you are explicitly evaluating the beta API surface
- the included Python package or Dockerfile
- operator-managed networking, TLS, backups, and secret handling

What is not currently bundled as first-class repo artifacts:

- a production `docker-compose` stack
- a Helm chart
- a managed cloud control plane
- contractual enterprise SLAs

Use this guide to harden what exists, not to assume missing platform layers already ship.

## Baseline Hardening Checklist

1. Pin an exact git tag or commit, built wheel, or container image for every environment.
2. Run behind a TLS-terminating reverse proxy rather than exposing the app directly to the internet.
3. Set `CORTEX_DEPLOY=cloud` in internet-facing environments so interactive docs are disabled.
4. Set `CORTEX_ALLOWED_ORIGINS` explicitly; do not leave localhost defaults in shared environments.
5. Persist the database on a dedicated volume and set `CORTEX_DB_PATH=/data/cortex.db`.
6. Run with a real encryption key source. In headless or containerized environments without OS keyring access, provide `CORTEX_MASTER_KEY` or `CORTEX_VAULT_KEY`.
7. Restrict filesystem access to the service user and the mounted data directory.
8. Keep the API authenticated and tenant-scoped; do not rely on network position alone.
9. Back up both the database and the encryption key material required to read encrypted facts.
10. Run periodic integrity checks such as `cortex trust-ledger verify --full` and portable `cortex export` snapshots.
11. Scan the built image and Python dependencies as part of your deployment pipeline.
12. Exercise restore and rollback procedures before calling the deployment production-ready.

## Secrets And Key Management

CORTEX uses OS keyring when available, with environment fallback for non-interactive environments.

For container or CI-style deployments:

- prefer injecting a base64-encoded `CORTEX_MASTER_KEY`
- treat that key as sensitive production secret material
- back it up separately from the SQLite database
- verify that operators can still decrypt persisted data after restart

Without key continuity, encrypted persisted data may become unreadable after redeploy.

## Optional Docker Posture For Self-Hosted API Beta

Use this only if you are evaluating the beta API deployment surface. It is not the primary supported core.

The included `Dockerfile` already helps with two basics:

- multi-stage build
- non-root runtime user

An operator-managed example:

```bash
docker build -t cortex:eval .

docker run --rm -d \
  --name cortex \
  -p 8484:8484 \
  -e CORTEX_DEPLOY=cloud \
  -e CORTEX_DB_PATH=/data/cortex.db \
  -e CORTEX_ALLOWED_ORIGINS=https://your-ui.example.com \
  -e CORTEX_MASTER_KEY=BASE64_32_BYTE_AES_KEY \
  -v cortex-data:/data \
  cortex:eval
```

Then validate the service:

```bash
curl -f http://127.0.0.1:8484/health
```

## Network And API Hardening

- terminate TLS at a reverse proxy or ingress
- restrict inbound access to trusted networks or authenticated clients
- set a narrow `CORTEX_ALLOWED_ORIGINS` value
- validate rate limiting for your traffic profile using `CORTEX_RATE_LIMIT` and `CORTEX_RATE_WINDOW`
- avoid enabling broad browser access until authentication and CORS are explicitly configured

## Data Protection

For SQLite-backed deployments:

- store the database on durable storage
- include WAL-aware backup procedures in operations
- monitor available disk space on the volume backing `/data`
- protect backup artifacts at the same sensitivity level as the live database

For environments using cloud backends, the operator remains responsible for:

- database backup strategy
- access control
- encryption and secret rotation
- regional placement and regulatory requirements

## Rollout And Rollback

Before declaring a release deployable:

- run the checklist in [DUE_DILIGENCE_CHECKLIST.md](DUE_DILIGENCE_CHECKLIST.md)
- build the package and container from the tagged source
- smoke-test `cortex init`, `cortex store`, `cortex verify`, and `GET /health`
- verify the service starts with the intended DB path and key material
- define a rollback path to the prior image/package and prior database backup

## Known Caveats

- the beta release line still requires operator judgment
- self-hosted maturity is stronger than distributed-cloud maturity
- historical docs may describe aspirational deployment paths that are not bundled artifacts yet

Treat this document, [VERSION_SUPPORT.md](VERSION_SUPPORT.md), and [ENTERPRISE_READINESS.md](ENTERPRISE_READINESS.md) as the current buyer-facing truth.
