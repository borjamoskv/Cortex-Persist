# RFC-002: L2 Vector Migration & Topological Resolution (C-EDG)

**Author:** MOSKV-1 APEX
**Date:** 2026-06-21
**Status:** ACCEPTED (C5-REAL EXECUTION)
**Target:** Cryptographic Epistemic Dependency Graph (C-EDG)

## 1. Context & Vulnerability (Brecha C-10 to C-14)
The initial C-EDG architecture attempted to preserve `cosine_similarity` under an affine orthogonal transformation `phi_K(x) = Q_K*x + T_K` to establish cryptographic vector isolation.
A rigorous formal attack demonstrated that **translation (`T_K`) mathematically destroys the cosine metric**, rendering Approximate Nearest Neighbors (ANN) functionality equivalent to stochastic noise.

## 2. Structural Resolution

### 2.1 Métrica Forzada: L2 (Euclídea)
Se aniquila la distancia coseno en todo el ecosistema CORTEX-Persist (`sqlite-vec`, `pgvector`, Qdrant).
Bajo Distancia Euclídea (L2), la transformación ortogonal con traslación SÍ es una isometría exacta:
`d(phi_K(u), phi_K(v)) = ||(Q_Ku + T_K) - (Q_Kv + T_K)|| = ||Q_K(u - v)|| = ||u - v|| = d(u, v)`
Esto preserva el recall del 100% en ANN mientras mantiene la entropía criptográfica inter-clave al máximo.

### 2.2 Geometría Estocástica vs Topología Determinista
HNSW es re-categorizado formalmente como un **Pre-Filtro Probabilístico**.
Las aristas del EDG jamás se anclan sobre la salida bruta de ANN. El subset retornado por HNSW es sometido a una **Validación L2 Exacta** (en memoria, post-descifrado) antes de materializar el Puente Topológico, garantizando que el Grafo Epistémico subyacente sea determinista.

### 2.3 Sellado de Puentes Covertos (ZK-SNARK)
Los puentes epistémicos inter-clave `e = (u_A, v_B)` ya no confían ciegamente en el Ledger. La resolución exige que el nodo `B` adjunte una prueba de conocimiento cero (ZK-Guard) demostrando que la procedencia estructural del vector cumple las invariantes del Causal Compiler sin revelar la clave `K_B`.

### 2.4 Consenso BFT Intra-Swarm
El aislamiento vectorial (Vector Isolation) se eleva a nivel de *Tenant / Swarm*, no de modelo o agente individual. El Swarm comparte la misma clave geométrica `K`, permitiendo validación matemática cruzada y votación fundamentada, mientras preserva aislamiento criptográfico estricto respecto a otros Tenants.

### 2.5 Frontera de Pareto
Se abandona la ilusión de maximizar Rendimiento simultáneamente con Seguridad y Precisión.
- **Seguridad:** Entropía MAX vía `Q_K` + `T_K`.
- **Precisión:** Recall EXACTO vía migración a L2.
- **Rendimiento:** Se acepta la penalización de latencia en la capa de filtrado exacto.

## 3. Migration Path
- `cortex/storage/pg_schema.py`: Reemplazo de `vector_cosine_ops` por `vector_l2_ops` o `vector_ops`.
- `cortex/engine/semantic_hash.py`: Reescritura de `cosine_similarity` a `euclidean_distance`.
- `cortex/storage/qdrant.py`: Configuración de colecciones a `Distance.EUCLID`.
