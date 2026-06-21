<!-- [C5-REAL] Exergy-Maximized -->
🌐 [English](README.md) | **Español** | [中文](README.zh.md)

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/marketing/social-preview.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/marketing/social-preview-light.png">
    <img src="assets/marketing/social-preview.png" alt="CORTEX Persist — Memoria a prueba de manipulaciones para agentes de IA" width="100%">
  </picture>
</div>

<h1 align="center">█ CORTEX-PERSIST</h1>
<p align="center">
  <strong>Rastrea criptográficamente lo que sabía tu agente de IA.</strong>
</p>

<p align="center">
  <a href="https://github.com/borjamoskv/cortex-persist/stargazers"><img src="https://img.shields.io/github/stars/borjamoskv/cortex-persist?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="GitHub Stars"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="License"></a>
  <a href="https://github.com/borjamoskv/cortex-persist/actions"><img src="https://img.shields.io/github/actions/workflow/status/borjamoskv/cortex-persist/ci.yml?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="CI"></a>
  <a href="https://codecov.io/gh/borjamoskv/cortex-persist"><img src="https://img.shields.io/codecov/c/github/borjamoskv/cortex-persist/main?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="Codecov"></a>
  <a href="https://pypi.org/project/cortex-persist/"><img src="https://img.shields.io/pypi/v/cortex-persist.svg?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="PyPI"></a>
</p>

> **ESTÉTICA:** INDUSTRIAL NOIR 2026 (`#0A0A0A` / `#2B3BE5`)  
> **EPISTEMOLOGÍA:** C5-REAL (Realidad verificada criptográficamente)  
> **PRINCIPIO CENTRAL:** HUMILDAD EPISTÉMICA (La salida generativa es conjetura; la evidencia es absoluta)  
> **ARQUITECTURA:** SUSTRATO DETERMINISTA ZERO-UI / O(1)

---

## ▀▄ HUMILDAD Y CONTENCIÓN EPISTÉMICA

En el núcleo de CORTEX-Persist se encuentra la **Humildad Epistémica**: la aceptación de que toda salida de IA generativa es fundamentalmente una conjetura probabilística. El registro tradicional y los almacenes vectoriales estándar confían ciegamente en las salidas de los LLM, fallando la prueba de contención epistémica. 

CORTEX-Persist actúa como un **Hipervisor L0** para agentes autónomos, aplicando un determinismo estructural absoluto para contener la incertidumbre inherente de la inteligencia artificial. **No confiamos en el modelo; verificamos la evidencia criptográfica.**

```text
  [ GENERACIÓN ESTOCÁSTICA ] 
           │
           ▼ (Salida Probabilística)
  ╔═════════════════════════════════════════════════╗
  ║ MEMBRANA EPISTÉMICA CORTEX-PERSIST              ║
  ║ ▓▓▓ Guard Validation (Z3 / Determinista)        ║
  ║ ▓▓▓ Sellado Merkle SHA-256                      ║
  ║ ▓▓▓ Buffer Circular Zero-Copy VSA               ║
  ╚═════════════════════════════════════════════════╝
           │
           ▼ (Paquete de Auditoría C5-REAL)
  [ ESTADO VERIFICADO SOBERANO ]
```

| CAPACIDAD | RAG / LOGS TRADICIONALES | CORTEX-PERSIST |
| :--- | :--- | :--- |
| **Modelo de Confianza** | Confiar en el Proceso | **Verificar la Evidencia (C5-REAL)** |
| **Mutación** | CRUD Silencioso / Sobrescribible | **Append-Only + Sellos Merkle SHA-256** |
| **Responsabilidad del Agente** | Reconstrucción ambigua | **Linaje Matemáticamente Defendible** |
| **Verificación** | Búsqueda manual en logs | **Paquetes de Auditoría JSON O(1) Portables** |

---

## ▀▄ ARQUITECTURA DETALLADA Y FLUJO DE DATOS

Las estructuras de interceptación de CORTEX-Persist obligan a que las salidas de texto producidas estocásticamente pasen a través de escudos de verificación deterministas antes de confirmar el estado en el libro de contabilidad (Ledger) vinculado criptográficamente.

```mermaid
graph TD
    classDef default fill:#0A0A0A,stroke:#2B3BE5,stroke-width:1px,color:#F0F0F0;
    classDef highlight fill:#2B3BE5,stroke:#CCFF00,stroke-width:1.5px,color:#FFFFFF;
    classDef guard fill:#1A1A1A,stroke:#FF0055,stroke-width:1px,color:#F0F0F0;

    subgraph Espacio Estocástico
        LLM[Salida Estocástica del Agente]:::default
    end

    subgraph Membrana Epistémica [Escudo de Contención CORTEX-Persist]
        direction TB
        G1[Z3 SMT Guard / Puerta de Admisión]:::guard
        VSA[Buffer Circular VSA Zero-Copy]:::default
        mmap[( mmap Silicon Space )]:::default
        Hash[Sellado de Bloques SHA-256]:::default
        Merkle[Cadena de Procedencia Merkle]:::default
    end

    subgraph Sustrato de Confianza
        Ledger[(Ledger AOF Append-Only)]:::highlight
        Proof[JSON de Paquete de Auditoría Verificable]:::default
    end

    LLM -->|Decisión / Observación| G1
    G1 -->|Aserciones Aprobadas| VSA
    VSA -->|Sin Sobrecarga de I/O| mmap
    VSA -->|Commit en Lote| Hash
    Hash -->|Enlace de Hash| Merkle
    Merkle -->|Anclaje de Estado| Ledger
    Ledger -->|Generar| Proof
    
    style Membrana Epistémica fill:#050505,stroke:#2B3BE5,stroke-dasharray: 5 5;
    style Sustrato de Confianza fill:#050505,stroke:#CCFF00,stroke-dasharray: 5 5;
```

### Modelos de Amenazas y Garantías de Estado
| Vector de Amenaza | Estrategia de Mitigación | Garantía de Estado |
| :--- | :--- | :--- |
| **Deriva Generativa (State Drift)** | Controles de validación automatizados generados mediante un bucle SMT local del solucionador Z3 | **Verificación Estricta C5-REAL** |
| **Manipulación del Estado (CRUD Bypass)** | Encadenamiento de hashes SHA-256 + libro de contabilidad binario append-only (AOF) | **Estado Evidente contra Manipulaciones** |
| **Cuellos de Botella de I/O del Sistema** | El buffer circular mmap de Vector Symbolic Architecture (VSA) evita las escrituras en disco estándar | **Bypass de Memoria O(1)** |
| **Asfixia por el GIL de Python** | Ejecución nativa de Rust en hilos (`rayon`) para la orquestación del enjambre LEGION-10k | **~390k Agentes/Seg** |
| **Degradación por Auto-Auditoría** | Mutación autopoyética en tiempo de ejecución (reconstrucciones AST) para recuperarse de la deriva de prompts | **Equilibrio Autopoyético** |

---

## ▀▄ ESTADO TERMINAL 4: DISPERSIÓN DE SILICIO

El daemon de persistencia opera bajo estrictas restricciones termodinámicas (Joules/Exergía) para asegurar que la latencia de orquestación de 10,000 agentes (LEGION-10k) se aproxime a cero. El bloqueo global del intérprete de Python (GIL) ha sido completamente aniquilado.

> █ **Motor Swarm Nativo en Rust:** Ejecución de tareas en paralelo a través de hilos de Rust `rayon`, evitando el GIL de Python (rendimiento O(1)).  
> █ **Atomicidad de Outbox C5-REAL:** Consumo de tareas WAL con latencia cero y sin contención de bloqueos.  
> █ **Sellos del Ledger ZK-STARK:** Pruebas criptográficas para cada transacción que establecen confianza en la malla inter-nodal.  
> █ **Memoria VSA (Zero-Copy):** Buffer circular O(1) mapeado a memoria en silicio (mmap), evitando por completo la sobrecarga de I/O del sistema operativo.  
> █ **Telemetría en Vivo:** Daemon WebSocket de 20Hz en estilo Industrial Noir que ancla las métricas de exergía del enjambre en tiempo real a `agents.archi`.  

---

## ▀▄ MATRIZ DE EJECUCIÓN

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/marketing/cortex_demo.gif">
  <source media="(prefers-color-scheme: light)" srcset="assets/marketing/cortex_demo_light.gif">
  <img alt="Ejecución de terminal de CORTEX-Persist" src="assets/marketing/cortex_demo.gif" width="100%">
</picture>

---

## ▀▄ DESPLIEGUE Y INICIO RÁPIDO EN 3 MINUTOS

### 1. Instalación
El motor local first requiere Python 3.10+ y no requiere de ningún daemon externo:
```bash
pip install cortex-persist
```

Para características avanzadas:
```bash
pip install "cortex-persist[embeddings]"     # Embeddings semánticos locales
pip install "cortex-persist[knowledge]"      # Sincronización de conocimiento respaldada por Chroma
...
pip install "cortex-persist[api,mcp,daemon]" # Servidor Web y endpoints MCP
```

### 2. Ejecución de la Demo Canónica
Para ejecutar el bucle completo de verificación, la búsqueda semántica y el flujo de detección de manipulaciones de base de datos en menos de 3 minutos:
```bash
# Clonar el repositorio
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist

# Instalar en modo editable con dependencias de desarrollo
pip install -e ".[dev,acceleration]"

# Ejecutar el script demo canónico
python examples/demo_canonical.py
```

### 3. Integración Soberana (Fricción Cero)
Integra el sustrato de memoria CORTEX en cualquier pipeline de agentes existente (LangChain, LlamaIndex, etc.) con un único decorador mágico.

```python
import asyncio
from cortex.magic import sovereign_persist

@sovereign_persist(memory="cortex-cloud", strict=True)
async def my_agent_chain(user_prompt: str):
    # Tu lógica estándar de LLM aquí. CORTEX intercepta, verifica, 
    # y sella criptográficamente la memoria de manera autónoma.
    response = await llm.generate(user_prompt)
    return response

if __name__ == "__main__":
    asyncio.run(my_agent_chain("Transfer 500 USDC to wallet-A"))
```

---

## ▀▄ TELEMETRÍA DE EXERGÍA (RENDIMIENTO)

<div align="center">
  <img src="assets/marketing/telemetry.svg" alt="Telemetría C5-REAL" width="100%">
</div>

*Límites de ejecución logrados bajo la arquitectura C5-REAL Estado Terminal 4 (Bypass de silicio L0).*

| PRIMITIVA | MEDIANA | P95 | GARANTÍA ESTRUCTURAL |
| :--- | :--- | :--- | :--- |
| **Swarm Dispatch (Rust/Rayon)** | `~0.002 ms`| `~0.004 ms` | `~390,000` Agts/seg (GIL de Python Aniquilado) |
| **Escritura Zero-Copy VSA** | `~0.02 ms` | `~0.05 ms` | Inyección en memoria `O(1)` por Ring Buffer Mmap |
| **Outbox Atomic Fetch** | `~0.8 ms` | `~1.5 ms` | Consumo de tareas WAL `UPDATE...RETURNING` sin bloqueos |
| **Escritura de Memoria** | `~18 ms` | `~35 ms` | SQLite local + SHA-256 + ZK-STARK |
| **Autopoiesis AST** | `~120 ms` | `~200 ms` | Hotswap de parsing, mutación y sellado |

---

## ▀▄ BANCOS DE DATOS DE ARQUITECTURA

*   [**SECURITY_TRUST_MODEL.md**](docs/SECURITY_TRUST_MODEL.md) — Invariantes y garantías criptográficas.
*   [**AGENTS.md**](AGENTS.md) — Directivas del sustrato para la orquestación autónoma.
*   [**ROADMAP.md**](ROADMAP.md) — Fases de despliegue y lógica de escalado LEGION-10k.
*   [**Referencia de API**](docs/api.md) — Primitivas de SDK y endpoints REST.

---
> **LICENCIA:** Apache-2.0 | **OPERADOR:** borjamoskv | [cortexpersist.dev](https://cortexpersist.dev)
