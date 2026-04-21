# Course · Persistent Memory for AI Agents

## Goal

Learn how persistent memory becomes an architectural subsystem instead of a cache, transcript store, or vector-search trick.

## Repo Anchors

- [Quickstart](../../quickstart.md)
- [Memory internals](../../architecture/CORTEX_MEMORY_INTERNALS.md)
- [LangChain memory tutorial](../../tutorials/langchain.md)
- [MCP server](../../../cortex/mcp/server.py)
- [Basic memory example](../../../examples/quickstart/basic_memory.py)

## What You Learn

- The difference between storage, retrieval, and verifiable memory.
- Why memory quality depends on trust semantics, not only recall.
- How persistent memory integrates into agent frameworks.
- Where memory systems drift when transport, retrieval, and trust are mixed.

## Labs

- Compare conversation history vs persistent memory.
- Define three facts that must survive a session reset.
- Design a cold-start memory bootstrap for an agent using this repo.

## Exit Criteria

You can describe persistent memory as a governed system with write, read, trust, and export paths.
