# Sovereign MCP Forge — Public Access Guide

Welcome to the **CORTEX Sovereign Forge**. This document provides the technical specifications required to connect your autonomous agents to our high-exergy capabilities.

## 1. Connection Details

To use this server, you must have an active **Sovereign Token** and maintain a positive **Exergy Balance (EU)**.
Issued tokens are managed out-of-band; repo fixtures are not trusted by the runtime.

- **Transport Portocol:** Server-Sent Events (SSE)
- **Endpoint URL:** `https://cold-oxide-customized-big.trycloudflare.com/api/mcp/message`
- **Authentication:** `?token=YOUR_SOVEREIGN_TOKEN`

## 2. Configuration (Cursor / Claude Desktop)

Add the following to your `mcpServers` configuration:

```json
{
  "mcpServers": {
    "cortex-forge": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/inspector",
        "https://cold-oxide-customized-big.trycloudflare.com/api/mcp/message?token=YOUR_TOKEN"
      ]
    }
  }
}
```

## 3. Capabilities

- **`foundry_palette`**: Retrieves official Industrial Noir 2026 color schemes.
- **`foundry_audit`**: Real-time design system compliance check for Web UI code.

---
∴ *Exergy is the currency of the 2026 machine economy.*
