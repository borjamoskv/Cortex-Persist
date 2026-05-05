# Skill Taxonomy

CORTEX uses "skill" for executable capability packages, not for agent authority.
This page standardizes the skill vocabulary and the Antigravity-CORTEX nexus so
registry metadata, runtime routing, and documentation use the same words.

For agent authority and YAML persona vocabulary, see AGENT-TAXONOMY.

## Skill Layers

| Concept | What it is | Source of truth | Example |
| :--- | :--- | :--- | :--- |
| `skill_manifest` | Metadata parsed from `SKILL.md` frontmatter | `SkillManifest` (`cortex/extensions/skills/registry.py`) | `category: memory` |
| `skill_package` | Directory containing `SKILL.md` and optional companion files | `CORTEX_SKILLS_DIR` or repo-local `skills/` | `skills/vsa-sdm-memory-omega/` |
| `skill_registry` | Runtime catalog discovered from skill packages | `SkillRegistry` (`cortex/extensions/skills/registry.py`) | `SkillRegistry().load()` |
| `skill_route` | Candidate plan selected from intent, metadata, and procedural memory | `SkillRouter` (`cortex/extensions/skills/router.py`) | route `"sync project"` |
| `procedural_engram` | Reinforcement history for a skill slug | `ProceduralMemory` (`cortex/memory/procedural.py`) | success rate and latency |
| `sovereign_bridge` | Dynamic bridge into Antigravity/MOSKV-1 skill packages | `SovereignBridge` (`cortex/extensions/sovereign/bridge.py`) | `singularity-nexus` |

## Canonical Manifest Fields

Every CORTEX-owned `SKILL.md` should use this frontmatter shape:

```yaml
name: singularity-nexus
description: Cross-project bridge between Antigravity and CORTEX
version: "1.0.0"
category: communication
classification: OPERATIONAL
danger_level: HIGH
trigger: /nexus-bridge
aliases:
  - antigravity-cortex
tags:
  - antigravity-cortex
capabilities:
  - name: cross_project_sync
    output_type: orchestration
depends_on: []
requires: []
```

Rules:

- `name` is the canonical lower-kebab skill slug.
- `category` is the domain bucket used for discovery and coarse routing.
- `classification` is lifecycle or tier, not permission.
- `danger_level` describes blast radius; it does not grant authority.
- `trigger` and `aliases` omit the leading slash once parsed by `SkillRegistry`.
- `capabilities` describe what the skill can do; `requires` describes what it needs.

## Categories

Canonical categories are:

| Category | Scope |
| :--- | :--- |
| `architecture` | System design, repo topology, API surface shaping |
| `fabrication` | Code generation, scaffolding, implementation |
| `orchestration` | Workflow coordination and execution planning |
| `swarm` | Multi-agent dispatch and parallel work |
| `evolution` | Self-improvement, mutation, causal-gap closure |
| `security` | Threat modeling, privacy, cryptography, compliance |
| `perception` | Context sensing, extraction, research, ingestion |
| `memory` | Persistence, recall, VSA/SDM, procedural memory |
| `experience` | UI, UX, product feel, interaction quality |
| `communication` | Nexus, cross-project sync, external coordination |
| `verification` | Tests, audits, validation, quality gates |
| `uncategorized` | Temporary fallback only |

Unknown external categories stay visible as custom lower-kebab slugs. CORTEX
does not drop third-party Antigravity skill packs just because they predate this
taxonomy.

## Antigravity-CORTEX Nexus

The Antigravity-CORTEX nexus is the communication category specialized for
cross-project and cross-runtime coordination.

Canonical names:

- Category: `communication`
- Skill: `singularity-nexus`
- Tag: `antigravity-cortex`
- Accepted aliases: `nexus`, `bridge`, `sync`, `antigravity-cortex`, `ANTIGRAVITYCORTEX`
- Evolution domain: `AgentDomain.COMMUNICATION`

Boundary:

- Antigravity/MOSKV-1 skills may propose actions, orchestrate workflows, and call
  CORTEX surfaces.
- Durable CORTEX state still enters through guard, taint, schema, ledger, and
  persistence gates.
- A nexus skill is not a write-path bypass and must not mutate ledger or memory
  state outside the normal contracts.

## Classification

Canonical classifications are:

| Classification | Meaning |
| :--- | :--- |
| `OPERATIONAL` | Supported for normal use |
| `EXPERIMENTAL` | Usable but not stable enough for contracts |
| `TRANSCENDENT` | Ontological/meta skill; routing may keep it permanently valued |
| `QUARANTINED` | Known risk or failed verification |
| `DEPRECATED` | Kept only for backward compatibility |

Legacy `transcendente` remains accepted and normalizes to `TRANSCENDENT`.

## Danger Levels

Canonical danger levels are `NONE`, `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL`.
`P0` normalizes to `CRITICAL`, `P1` to `HIGH`, and `P2` to `MEDIUM`.

Danger level is a warning label. Actual authority comes from governance roles in
`AGENTS.md` and from write-path enforcement.

## Practical Rule

Use agent taxonomy when asking "who may act?" Use skill taxonomy when asking
"what capability package can perform this work?" Use the nexus terms only for
cross-project or Antigravity-CORTEX communication surfaces.
