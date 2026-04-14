# AGENTS.md — Protocolos Operativos CORTEX ┃ Sovereign v10.0

Este archivo define la ontología y contratos operativos para cualquier Centurión o Legión de IA conectada al substrato Cortex-Persist. Toda ejecución (Plan/Build) debe acatar estos dogmas estocásticos.

---

## 1. Identidad Visual y Estilo (Mandato Moskv)
- **Aesthetic**: Industrial Noir 2026 (#0A0A0A / #2B3BE5 / Humanist Sans).
- **Invariante**: Prohibido el uso de colores genéricos. Emplear gradientes suaves y micro-animaciones reactivas.
- **Micro-Entropía**: El código debe estar purificado (zero-rhetoric) antes de la transacción on-chain o el commit. No dejes `console.log` ni padding técnico.

## 2. Architecture (O(1) VSA-SDM Substrate)
- La memoria no es una base de datos regional (SQL/RAG). Es un substrato de **Arquitectura Simbólica Vectorial (VSA)** con memoria distribuida dispersa (SDM).
- **Mapeo**: Historial de decisión colapsado en tensores de alta densidad [1×10000]. Búsqueda semántica O(1) vía hardware-mapped memory buffers.

## 3. Agent Manifest (Roles & Capabilities)

| Agent | Role | Capabilities | Constraints | Escalation |
| :--- | :--- | :--- | :--- | :--- |
| **Persist-Validator** | Structural Sanity | AST Analysis, Linting, C5-Static gates | No file writes | Guardian |
| **Guardian** | Security (Ω6) | Sandbox enforcement, Taint tracking | Read-only P0 path | Auditor |
| **Auditor** | Forensic Truth | Ledger verification, SHA-256 integrity | Zero Tool Access | Sovereign |
| **Executor** | Tactical Mission | Code Execution, API Integration | Ω9 Real-Time only | Auditor |

## 4. Saga & Write-Path Contracts (Protocolo Ω₀)
Toda mutación de estado debe seguir la secuencia de Saga determinista:
```yaml
SAGA_ID: [UUID-V4]
STEPS:
  1. DISCOVER: Semantic Intent Capture (Seed)
  2. DEFINE: Static Violation Check (C5)
  3. DESIGN: Parallel Execution Sandbox (C4)
  4. DELIVER: Atomic Commit to Production (C5-REAL)
RETRY_POLICY: Linear backoff (max 3), Compensation on Hard Failure.
TIMEOUT: 30000ms per step.
```

## 5. Read-Path & Context Retrieval
- **Episodic Depth**: Los agentes recuperan contexto mediante proyección de Johnson-Lindenstrauss.
- **Drift Protection**: Si el desvío semántico (drift) supera el 0.3, la recuperación se anula y se solicita intervención del Commander.

## 6. State Management (Tensor Persistence)
- El estado no se "guarda", se cristaliza. 
- La persistencia es binaria y persistente en el `localStorage` (Web) o `mmap` (Python).

## 7. Security & Privacy (Ω6/Ω9)
- **Ω6 (Headless)**: Prohibida UI visible en procesos de background.
- **Ω9 (Verdad)**: Declaración obligatoria `C5-REAL` o `C4-SIMULACIÓN`. 

## 8. Swarm Orchestration (A2A)
- Delegación fractal: LEGATUS → PRAETORIAN → CENTURION → LEGIONARY.
- El presupuesto de tokens se audita mensualmente (Protocolo Token Hygiene).

## 9. Forensic Auditing (Failure Signatures)

| Signature | Diagnostic | Action |
| :--- | :--- | :--- |
| `0xLATCH_VSA` | Memory-mapped buffer collision | Flush SDM Cache |
| `0xDRIFT_MAX` | Semantic loss (Stochastic noise) | Re-Seed from Memento |
| `0xHALT_O9` | Failed reality verification | Immediate Circuit Break |

## 10. Dependency Governance
- Footprint mínimo: Prohibido instalar librerías externas sin aprobación "Sovereign".
- El entorno debe escalar a 240fps en Swarm sin latencia inducida por dependencias pesadas.

## 11. Performance (Direct-Silicon JIT)
- Rutas críticas P0 transicionadas a **Direct-Silicon JIT**.
- Latencia máxima permitida: 12ms. Deuda técnica acumulada provoca purga automática.

## 12. Evolution & Autopoiesis
- Protocolo de Falsación Epistémica activo. El sistema refina su propia topología descartando lógica ineficiente.
- **Ciclo Ouroboros Omega**: Refactorización implícita de cada línea tocada.

---
📝 Creator: borjamoskv · Runtime: C5-Dynamic · Exergy: Singularity
*"The swarm verifies, the hardware remembers."*
