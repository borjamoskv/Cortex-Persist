# CORTEX Persist Operations

This page is the repo-versioned operational overview for the currently supported product surface.

## Supported Operating Modes

| Mode | Status | Notes |
| :--- | :--- | :--- |
| Local source install | Most mature | `pip install .` with SQLite and the CLI/local core is the primary operator path today. |
| Self-hosted API | Beta | Run from the same source checkout with `pip install -e ".[api]"` and operator-managed infra. |
| Worker stack | Experimental / outside supported core | `deploy/compose/` and `deploy/k8s/` exist in-repo, but should not be treated as a supported product path today. |
| Managed cloud distribution | Not yet public | Treat cloud-scale and managed-service positioning as roadmap until explicitly released. |

## Cross-Platform Posture

The source-install path is designed to run on:

- macOS
- Linux
- Windows

The exact daemonization and notification surfaces differ by platform, but the CLI and SQLite-backed local mode remain the common baseline. API startup is an optional beta surface from the same source checkout.

## Core Operational Checks

```bash
cortex status
cortex trust-ledger verify --full
python -m pytest tests/test_core_paths.py tests/test_public_memory_service.py tests/test_ledger_l3.py -q
```

For optional API beta mode:

```bash
pip install -e ".[api]"
uvicorn cortex.api:app --port 8000
curl http://localhost:8000/v1/status
```

## Backup And Verification

- Back up the SQLite database file before invasive maintenance.
- Run ledger verification after imports, repair work, or unexpected shutdowns.
- Treat failed verification as a trust event, not a cosmetic warning.

## Release Channels

| Channel | Current Reality |
| :--- | :--- |
| GitHub source checkout | Available now |
| GitHub Releases | Workflow and signing path are configured, but only completed tagged releases should be treated as public artifacts |
| PyPI | Packaging is configured, but publication should not be advertised as available until artifacts are live |
| npm | SDK package exists in-repo, but public npm publication should not be advertised until it resolves successfully |

## Related References

- [Supported Core](supported-core.md)
- [Canonical Demo](canonical-demo.md)
- [API Reference](api.md)
- [Security & Trust Model](SECURITY_TRUST_MODEL.md)
- [Architecture](architecture.md)
- [DEPLOYMENT_HARDENING.md on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/DEPLOYMENT_HARDENING.md)
