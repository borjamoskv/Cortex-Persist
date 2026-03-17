# [TECHNOLOGY] Google A2A Protocol (Agent-to-Agent)

## 1. Core Primitives (O(1) Definitions)
- `A2A`: Protocolo abierto de Google (Abril 2025) para comunicación inter-agente. Contribuido a la Linux Foundation en Junio 2025.
- `Client-Server Model`: Agentes "cliente" formulan y comunican tareas; agentes "remotos" las ejecutan. HTTPS + JSON-RPC 2.0.
- `Agent Cards`: Archivos JSON de capability discovery. Cada agente publica qué sabe hacer.
- `Task Lifecycle`: Estados de ciclo de vida definidos para gestión de tareas distribuidas.
- `A2A vs MCP`: MCP = cómo un agente interactúa con tools/servicios externos. A2A = cómo agentes se comunican ENTRE SÍ. Complementarios.
- `150+ organizations by July 2025`: Atlassian, LangChain, MongoDB, PayPal, Salesforce, SAP, ServiceNow.
- `Status (Sept 2025)`: Desarrollo ralentizado. El ecosistema consolida mayoritariamente en torno a MCP.

## 2. Industrial Noir Paradigms (Adaptation)
- **Agent Cards = Skill Discovery**: Las Agent Cards de A2A son el equivalente de los archivos SKILL.md en el filesystem de MOSKV-1. Publicar capacidades para que otros agentes descubran qué puede hacer cada uno.
- **A2A para LEGION-1**: Si el enjambre spawnea agentes en máquinas distintas (ej. un servidor remoto + local), A2A sería el protocolo de comunicación estándar.
- **MCP Wins (Pragmatismo)**: El consolidamiento hacia MCP indica que MOSKV-1 debería priorizar MCP sobre A2A para interoperabilidad, y usar A2A solo si necesita federación inter-nodo real.

## 3. Copy-Paste Arsenal
```json
// Agent Card (capability discovery for MOSKV-Josu)
{
  "name": "moskv-josu-night-shift",
  "description": "Autonomous background agent for code generation, testing and deployment",
  "url": "https://localhost:8443/a2a",
  "capabilities": {
    "streaming": true,
    "pushNotifications": true
  },
  "skills": ["code_generation", "testing", "git_operations", "deployment"]
}
```
