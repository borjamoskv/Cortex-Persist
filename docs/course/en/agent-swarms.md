# Course · AI Agent Swarms

## Goal

Understand how a swarm becomes a governed system instead of a pile of parallel workers.

## Repo Anchors

- [Swarm routes](../../../cortex/routes/swarm.py)
- [Supervisor agent](../../../cortex/agents/builtins/supervisor_agent.py)
- [Aether daemon](../../../cortex/extensions/aether/daemon.py)
- [Consensus tutorial](../../tutorials/consensus.md)
- [Swarm dashboard](../../../scripts/swarm_dashboard.py)

## What You Learn

- The difference between orchestration, supervision, and consensus.
- Why swarm systems need explicit control planes.
- How worktrees, lifecycle operations, and voting surfaces fit together.
- Where swarm systems drift into security and maintenance debt.

## Labs

- Draw the boundary between agent runtime and operator surface.
- List three failure modes for a swarm with no shared verification layer.
- Propose one consolidation helper that would reduce swarm surface divergence.

## Exit Criteria

You can explain a swarm as a governed architecture with lifecycle, visibility, and trust boundaries.
