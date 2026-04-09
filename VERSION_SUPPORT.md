# Version Support

This document defines the support posture for public CORTEX Persist release lines.

It applies to published release lines and tagged artifacts. It does not automatically extend support to every experimental or repo-internal surface that may exist on `main`.

## Current Policy

| Release line | Status | Support posture |
| :--- | :--- | :--- |
| `0.3.x` beta | Active | Best-effort fixes, security triage, and documentation maintenance |
| `< 0.3.0` | Unsupported | Upgrade required before support review |

## Interpretation

- **Active** means the release line is still considered current for issue triage and security review.
- **Unsupported** means fixes are not backported and support requests may be redirected to upgrade first.
- **Beta** means the project may still change quickly, even if the technical surface is already substantial.

## Lifecycle Notes

- The current policy is line-based, not date-based.
- Support for the active beta line ends when a newer public line supersedes it or the policy is revised explicitly in-repo.
- Unsupported lines do not receive routine backports.

## Backport Policy

- By default, fixes land forward on the active line.
- Security or stability fixes are not promised as backports unless explicitly stated for a release line.
- Buyers who need dated maintenance commitments or LTS behavior should treat that as a separate commercial discussion rather than an implied repository policy.

## Compatibility Baseline

- **Python:** `>=3.10`
- **Primary package:** `cortex-persist`
- **Preferred source of truth for current metadata:** [pyproject.toml](pyproject.toml)

## Enterprise Guidance

If you are evaluating CORTEX for production or acquisition:

- pin exact versions during evaluation
- review [RELEASE_PROCESS.md](RELEASE_PROCESS.md) for the tagged Python publication flow
- align support expectations through [SUPPORT.md](SUPPORT.md)
- treat roadmap items as non-contractual unless separately agreed
