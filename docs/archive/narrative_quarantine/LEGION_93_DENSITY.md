---
cat_id: legion-93-density
cat_type: architecture
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
---

# C5-REAL TENSOR: Swarm Densification (LEGION-93)

> **"La entropía se purga mediante compresión termodinámica absoluta."** — Borja Moskv (Γ1)

Matriz condensada de la estructura agéntica de BABYLON-60. Proporciona la entropía de distribución de los 93 nodos agénticos.

## 1. Distribución por Proveedor (Provider Distribution)

| Proveedor | Nodos | Porcentaje | Nodos Clave / Desviaciones |
|:---|:---:|:---:|:---|
| **gemini** | 89 | 95.7% | Ecosistema core (pro y flash) |
| **google** | 1 | 1.1% | `auditor_omega` |
| **ollama** | 2 | 2.2% | `autonomo`, `mejoralo_omega` (Locales) |
| **groq** | 1 | 1.1% | `grammy_electronic` (Latencia ultra-baja) |

## 2. Distribución por Intento Cognitivo (Intent Distribution)

| Intento | Nodos | Porcentaje | Foco Primario |
|:---|:---:|:---:|:---|
| **reasoning** | 54 | 58.1% | Planificación, inferencia analítica y lógica |
| **code** | 32 | 34.4% | Mutaciones de AST, refactorizaciones y scripting |
| **architect** | 6 | 6.5% | Diseño de topología, consistencia física y gobernanza |
| **synthesis** | 1 | 1.1% | `notebooklm` (Compresión de contexto) |

## 3. Distribución por Tier de Exergía (Exergy Tier Distribution)

| Tier | Nodos | Porcentaje | Nivel de Control |
|:---|:---:|:---:|:---|
| **P0** | 1 | 1.1% | `demiurge` (Soberanía absoluta, control del plan) |
| **P1** | 92 | 98.9% | Nodos de producción y ejecución de tareas |

> [!IMPORTANT]
> **Auditoría Epistémica (Discrepancia P0/P1):** 
> Se ha identificado una discrepancia en la matriz de enrutamiento anterior. `prometheus` figuraba como `P0` en el tensor de diseño, pero su archivo de configuración física `prometheus.yaml` define estrictamente `exergy_tier: P1`. Se ha procedido a la corrección y sincronización directa en `docs/design/C5_ROUTING_TENSOR.md`.

## 4. Desviaciones Detectadas (Outliers)
Nodos configurados con entornos locales o proveedores de contingencia para mitigar fallas de red:
- `autonomo` (`ollama:qwen2.5-coder:32b`) - Autarquía local.
- `mejoralo_omega` (`ollama:qwen2.5-coder:32b`) - Refactorización y purga asíncrona local.
- `grammy_electronic` (`groq:llama-3.3-70b-versatile`) - Procesamiento de eventos en tiempo real.
