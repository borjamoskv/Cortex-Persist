# Security Policy

## Supported Versions

| Version | Supported          |
|:--------|:------------------:|
| 8.x     | ✅ Active          |
| < 8.0   | ❌ No longer       |

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Email: **security@cortexpersist.com**

You will receive an acknowledgment within 48 hours and a detailed response within 5 business days.

## Security Features

CORTEX is built security-first:

- **SHA-256 hash-chained ledger** — tamper-evident fact storage
- **Merkle tree checkpoints** — batch integrity verification
- **Privacy Shield** — 11-pattern secret detection at ingress
- **AST Sandbox** — safe LLM code execution without `eval()`
- **RBAC** — 4-role access control (admin, editor, viewer, auditor)
- **Security Headers Middleware** — CSP, HSTS, X-Frame-Options
- **Input Sanitization** — all user inputs validated and escaped

## Threat Model

CORTEX assumes:
- The local SQLite database is as secure as the host filesystem
- Network APIs require authentication (API keys or JWT)
- Multi-tenant deployments enforce strict tenant isolation
