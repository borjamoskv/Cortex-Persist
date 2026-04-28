# Agent Taxonomy

This repo uses the word "agent" for several different things. This page separates
the concepts so policy, implementation, and configuration do not get mixed.

## The Four Layers

| Concept | What it is | Source of truth | Typical example |
| :--- | :--- | :--- | :--- |
| `governance_role` | Authority boundary and permission model | [`AGENTS.md`](../../AGENTS.md) | `Persist-Auditor` |
| `builtin_agent` | Python class already implemented in the runtime | [`cortex/agents/builtins/`](../../cortex/agents/builtins/) | `SupervisorAgent` |
| `agent_definition` | Declarative YAML spec for name, model, prompt, tools, memory, and guardrails | [`cortex/extensions/agents/definitions/`](../../cortex/extensions/agents/definitions/) | `antigravity.yaml` |
| `agent_instance` | Hydrated runtime object created from a YAML spec | [`cortex/agents/loader.py`](../../cortex/agents/loader.py) | `AgentInstance` |

## 1. Governance Roles

Governance roles are policy, not code and not catalog entries.

- They define what an agent is allowed to do.
- They live in [`AGENTS.md`](../../AGENTS.md).
- They are the authority layer for trust, write-path, audit, and escalation rules.

Examples:

- `Persist-Validator`
- `Persist-Executor`
- `Persist-Auditor`
- `Persist-Guardian`

Use this layer when the question is "what may this agent do?"

## 2. Builtin Agents

Builtin agents are concrete Python implementations shipped with the runtime.

- They live under [`cortex/agents/builtins/`](../../cortex/agents/builtins/).
- They are imported and exported through [`cortex/agents/builtins/__init__.py`](../../cortex/agents/builtins/__init__.py).
- Their behavior is defined in code, not in YAML.

Examples:

- `SupervisorAgent`
- `VerificationAgent`
- `MemoryAgent`

Use this layer when the question is "which class implements this behavior?"

## 3. YAML Agent Definitions

YAML agent definitions are declarative specs for configurable agents.

- They live in [`cortex/extensions/agents/definitions/`](../../cortex/extensions/agents/definitions/).
- They are registered by [`AgentRegistry`](../../cortex/extensions/agents/registry.py).
- `AgentCatalogEntry` in that registry is the catalog dataclass; `AgentDefinition`
  remains only as a legacy alias for older imports.
- The registry scans top-level `*.yaml` files in that directory.
- `id` comes from the filename stem.

Each YAML definition can declare:

- `name`
- `model`
- `system_prompt`
- `provider`
- `intent`
- `tools`
- `memory`
- `guardrails`

Use this layer when the question is "which persona/model/tooling config do we want?"

## 4. Runtime Agent Instances

Runtime instances are what the system actually executes after loading a YAML file.

- [`DeclarativeAgentSpec`](../../cortex/agents/schema.py) is the schema for a YAML file.
- [`load_agent()`](../../cortex/agents/loader.py) reads that YAML and validates it.
- [`compile_agent()`](../../cortex/agents/loader.py) turns it into an `AgentInstance`.

Important:

- `DeclarativeAgentSpec` means "schema for a declarative agent definition".
- It does not mean the governance roles from [`AGENTS.md`](../../AGENTS.md).
- `AgentRole` remains only as a backward-compatibility alias for older imports.

Use this layer when the question is "what object is running in memory?"

## Practical Rule

If a discussion mixes these layers, confusion follows quickly.

- For permissions and authority, use `governance_role`.
- For code ownership and implementation, use `builtin_agent`.
- For configurable personas and prompts, use `agent_definition`.
- For the hydrated executable object, use `agent_instance`.

## Registry Boundary

The default YAML catalog is narrower than the whole folder tree.

- [`AgentRegistry.load_all()`](../../cortex/extensions/agents/registry.py) scans top-level `definitions/*.yaml`.
- Nested profile files are not auto-registered unless another path loads them explicitly.
- Builtins are separate from the YAML registry.

That means "listed in the repo" and "registered in the active catalog" are not always the same thing.
