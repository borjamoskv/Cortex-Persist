# Plugin Registry Architecture

> Specification for the CORTEX Plugin Registry — how plugins are discovered, verified, and distributed.

## Overview

The plugin registry is CORTEX's mechanism for discovering, distributing, and verifying plugins. It operates on a **trust-tiered model** where plugins earn verification levels through code review, automated scanning, and production usage.

## Trust Levels

| Level | Badge | Requirements | Install Behavior |
|:---|:---:|:---|:---|
| **Verified** | 🟢 | Core team review + Sigstore signed + 30d production use | Auto-install |
| **Community** | 🔵 | Automated scan passed + manifest valid + tests pass | Install with notice |
| **Experimental** | 🟡 | Valid manifest only | Install with warning |
| **Untrusted** | 🔴 | No validation | Blocked by default |

## Plugin Manifest Schema (v1)

```yaml
# manifest.yaml — required in every plugin
name: my-plugin               # unique slug
version: 0.1.0                # semver
description: "What it does"
author: Name <email>
license: MIT

runtime:
  type: docker                 # docker | wasm (future)
  image: org/plugin:tag
  
capabilities:
  - name: action_name
    description: "What this capability does"
    endpoint: /action
    method: POST

trust:
  min_cortex_version: "8.0"
  sandbox: true                # must run in container
  network: false               # no outbound network access
  filesystem: false            # no host filesystem access
```

## Discovery Mechanism

### Phase 1 (Current): GitHub-Based

- Plugins are GitHub repositories with topic `cortex-plugin`
- Discovery via GitHub Search API: `topic:cortex-plugin`
- Install via: `cortex plugin install github:org/repo`

### Phase 2 (Q3 2026): Registry API

```
GET  /api/v1/plugins                    # list all
GET  /api/v1/plugins/{name}             # get plugin details
GET  /api/v1/plugins/{name}/versions    # list versions
POST /api/v1/plugins                    # publish (authenticated)
```

Hosted at: `registry.cortexpersist.com`

### Phase 3 (Q4 2026): Federated Registries

Organizations can host private registries:

```bash
cortex config set registry https://registry.internal.acme.com
cortex plugin install acme/internal-plugin
```

## Security Model

1. **All plugins run in containers** — no direct host access
2. **Network isolation by default** — plugins declare network needs in manifest
3. **Sigstore verification** — verified plugins have signed images
4. **Automated scanning** — Trivy scans on every version publish
5. **Revocation** — compromised plugins can be revoked via registry API

## Governance

- **Core plugins** (maintained by CORTEX team): Standard review process
- **Community plugins**: PR-based review for "Community" level promotion
- **Dispute resolution**: GitHub Issues on the registry repository
