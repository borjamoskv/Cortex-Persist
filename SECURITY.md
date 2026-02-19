# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 4.x     | ✅ Active support  |
| 3.x     | ⚠️ Security fixes only |
| < 3.0   | ❌ End of life     |

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email **borjamoskv@gmail.com** with:

1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact assessment
4. Suggested fix (if any)

We will acknowledge receipt within **48 hours** and provide a timeline for resolution within **5 business days**.

## Security Architecture

### Authentication
- API key authentication via `X-API-Key` header
- Tenant isolation via `X-Tenant-ID` header
- Permission-based access control (`read`, `write`, `admin`)

### Data Protection
- All data encrypted at rest (SQLite with WAL mode)
- TLS 1.3 enforced in production deployments
- API keys are hashed, never stored in plaintext
- No telemetry or data collection — fully sovereign

### Supply Chain
- Dependencies pinned in `pyproject.toml`
- Automated dependency auditing via CI/CD
- No runtime network calls except to configured LLM providers

## Disclosure Policy

We follow [responsible disclosure](https://en.wikipedia.org/wiki/Responsible_disclosure). Security researchers who report valid vulnerabilities will be credited in the CHANGELOG (with permission).
