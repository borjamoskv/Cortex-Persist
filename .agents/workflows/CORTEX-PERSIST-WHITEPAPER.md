---
description: Cortex-Persist Whitepaper v0.2 — Infraestructura de gobernanza cognitiva para enjambres de agentes
---

# Cortex-Persist

## Infraestructura de gobernanza cognitiva para continuidad de memoria, resolución de colisiones y consistencia operacional en enjambres de agentes autónomos

---

## 0. Estado

**Normative Draft v0.2** — 2026-03-14

---

## 1. Resumen ejecutivo

Cortex-Persist propone una arquitectura de continuidad cognitiva para sistemas multi-agente basados en modelos fundacionales.

La tesis central es simple: la persistencia pasiva de embeddings no equivale a memoria fiable. En sistemas de larga duración, la combinación de RAG, similitud semántica y contexto acumulado genera entropía cognitiva: recuperación de hechos obsoletos, inferencias inválidas y contradicciones no resueltas.

Para resolver este problema, Cortex-Persist sustituye el modelo de “base vectorial + prompt” por una infraestructura de gobernanza cognitiva activa. La unidad básica ya no es el chunk, sino el Belief Object: una estructura con contenido semántico, estado epistémico, procedencia verificable, relaciones lógicas y política temporal de decaimiento.

Sobre esta ontología, el sistema introduce cuatro capacidades centrales:

1. revisión bayesiana de creencias,
2. mantenimiento de verdad condicionado por dependencias,
3. resolución de colisiones semánticas en enjambres distribuidos,
4. trazabilidad criptográfica del linaje de inferencia.

El resultado no es una memoria más grande, sino una memoria más gobernable.

---

## 2. Problema

La mayoría de arquitecturas agentic actuales confunden retención con memoria.

Persistir conversaciones, tool calls, embeddings y logs mejora la capacidad de recuperación, pero no resuelve el problema central de continuidad cognitiva: cómo mantener un estado de creencias coherente, auditable y revisable a lo largo del tiempo.

Cuando un agente opera durante semanas o meses, la memoria deja de degradarse por olvido y empieza a degradarse por acumulación. La recuperación semántica devuelve elementos parecidos, no necesariamente válidos. El sistema puede entonces reinyectar como contexto creencias ya invalidadas, hipótesis especulativas o eventos episódicos descontextualizados. A este fenómeno lo llamamos entropía del conocimiento.

Cortex-Persist aborda este límite sustituyendo la persistencia pasiva por una capa activa de gobernanza cognitiva. Su función no es almacenar más, sino decidir qué puede entrar en contexto, bajo qué condiciones, con qué confianza y con qué trazabilidad.

---

## 3. Objetivos y no-objetivos

### No-objetivos

Cortex-Persist no garantiza:

- Verdad objetiva del mundo,
- Satisfacibilidad lógica global en tiempo de ingestión,
- Consenso bizantino en redes arbitrariamente hostiles,
- Latencia constante bajo cualquier carga,
- Borrado semántico de salidas ya expuestas a terceros modelos.

---

## 4. Modelo del sistema

El sistema opera como un hipervisor cognitivo descentralizado estructurado en tres planos formales:

1. **Plano de Creencias:** Gestiona los *Belief Objects*, la máquina de estados y el mantenimiento de la verdad basado en suposiciones (ATMS).
2. **Plano de Integridad:** Garantiza la inmutabilidad y procedencia mediante Sparse Merkle Trees (SMT), cadenas de hash y firmas criptográficas.
3. **Plano de Coordinación:** Orquesta la propagación de estado a través del enjambre mediante CRDTs semánticos sobre transporte Zenoh, resolviendo colisiones con algoritmos de consenso bayesiano (LogOP).

Los agentes producen hechos. El *Memory Scheduler* dicta la inyección de contexto. El protocolo de consenso propaga los estados. La memoria compartida en Rust (iceoryx2) provee IPC lock-free hacia los pipelines de inferencia.

---

## 5. Belief Objects

La memoria no se almacena en vectores de texto aislados (chunks). Se almacena en *Belief Objects*. Sin esta máquina de estados, la persistencia semántica sigue siendo estadística ciega.

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BeliefState {
    Active,
    Contested,
    Subsumed,
    Discarded,
    Archived,
}

#[derive(Debug, Clone)]
pub enum RelationType {
    Entails,
    Discards,
    DependsOn,
    Supersedes,
}

#[derive(Debug, Clone)]
pub struct ProvenanceEnvelope {
    pub source_hash: String,
    pub source_type: String,
    pub tenant_id: String,
    pub signer_id: String,
    pub signature: String,
    pub created_at: i64,
}

#[derive(Debug, Clone)]
pub struct BeliefRelation {
    pub relation_type: RelationType,
    pub target_id: uuid::Uuid,
}

#[derive(Debug, Clone)]
pub struct BeliefObject {
    pub id: uuid::Uuid,
    pub proposition: String,
    pub confidence_score: f32,
    pub uncertainty: f32,
    pub decay_rate: f32,
    pub state: BeliefState,
    pub provenance: ProvenanceEnvelope,
    pub relations: Vec<BeliefRelation>,
    pub timestamp_created: i64,
    pub timestamp_last_verified: i64,
}
```

---

## 6. Gobernanza cognitiva

Si la memoria se gobierna, el conocimiento se limpia.

Cuando entra una pieza de evidencia que contradice una creencia activa, Cortex-Persist no la sobreescribe (sobrescribir destruye el linaje) ni promedia los vectores (eso crea amalgamas sin sentido).

El sistema:
1. Pasa el estado de la creencia a `Contested`.
2. Activa una revisión bayesiana para recalibrar el `confidence_score`.
3. Propaga la invalidación a cualquier creencia subordinada (dependencias `DependsOn`) en tiempo $O(1)$ gracias a los índices estructurales del ATMS (Assumption-based Truth Maintenance System).

Ninguna creencia vive sola. Si cae el cimiento, cae la estructura subordinada de inferencias.

---

## 7. Swarm Sync y resolución de conflictos

Sincronizar 100 agentes autónomos requiere convergencia matemática sin bloqueo.
El sistema emplea **CRDTs Semánticos** (Tipos de Datos Replicados Libres de Conflictos). 

A diferencia de los CRDTs estándar basados en el reloj del sistema (LWW - Last Writer Wins), el modelo de Cortex prioriza la causalidad lógica. LWW es peligroso en sistemas cognitivos: un reloj más reciente no hace que un argumento sea más válido.

Si dos agentes divergen fuertemente:
- Se invoca la capa de consenso (LogOP - Logarithmic Opinion Pool).
- Los vetos aplican una penalización epistémica saturante. 
- La aniquilación total de un consenso ($P \to 0$) requiere quórum reforzado (≥ 2/3) o una auditoría de Nivel 3 explícita. Nadie borra la memoria del enjambre unilateralmente.

---

## 8. Memory Scheduler

El programador de memoria evalúa una ecuación tensorial en cada ciclo de inferencia.
Calcula un puntaje explícito para decidir qué Belief Objects se inyectan en el prompt:

$$ \text{Score}(m) = \frac{(\text{Rel} \cdot w_r) + (\text{Conf} \cdot w_c) + (\text{Rec} \cdot w_t)}{\text{Cost}_{\text{tokens}} + \text{Risk}_{\text{contam}}} $$

Si el factor $\text{Risk}_{\text{contam}}$ (riesgo de contaminación estructural por contradicciones no resueltas en el subgrafo) supera los límites operativos, el Score colapsa a 0. La memoria se excluye de la inferencia, sin importar cuán similar sea el vector a la consulta (RAG bypass).

---

## 9. Integrity & Provenance

*Fronteras de confianza*

Una firma válida autentica autoría, no veracidad.
Una procedencia verificable no implica que el contenido sea correcto.
La activación de una creencia requiere más que integridad criptográfica: requiere admisibilidad epistémica bajo contexto, fuente y conflicto.

El linaje criptográfico es innegable. Todo cambio de estado (`BeliefState`) o adición matemática es un evento sellado en un Sparse Merkle Tree (SMT). Se puede generar una justificación criptográfica (ZKP) del origen exacto de cualquier conclusión del enjambre, trazable hasta la telemetría episódica bruta.

---

## 10. Threat model

Vectores de ataque epistémico y defensas estructurales de la arquitectura:

| Amenaza | Mecanismo de Defensa |
|:---|:---|
| **Envenenamiento Semántico** | Ponderación LogOP condicionada al historial (*proof-of-expertise*) |
| **Consenso Sesgado** | Restricciones de diversidad del enjambre + detección de anomalías |
| **Partición de Red** | Convergencia topológica CRDT sin necesidad de Master node |
| **Veto Malicioso** | Penalización epistémica saturante + auditoría humana escalada |
| **Ataque de Replay** | Marcos de causalidad estricta y relojes monótonos CRDT |

---

## 11. Failure modes

| Fallo Estructural | Consecuencia Operativa | Modo de Recuperación |
|:---|:---|:---|
| **Corrupción de Raíz SMT** | Pérdida de integridad demostrable del linaje | Rollback a último snapshot avalado; reconstrucción por tombstones |
| **Oscilación de Consenso** | Divergencia LogOP infinita | Límite por decaimiento termodinámico; auto-suspensión (*circuit breaker*) |
| **Fallo Posición Índice (Partición)** | Dependencias `DependsOn` huérfanas retenidas | Limpieza total de subgrafos tras reconvergencia Edge |
| **Falso Negativo Scheduler** | Alucinación inyectada a zona L1 | Barrera de defensa en profundidad; red-teaming cíclico |

---

## 12. SLOs / Objetivos operativos

Estas son las métricas TARGET del sistema bajo carga nominal, especificadas como objetivos, no promesas divinas.

| Operación | TARGET Operativo | Condición de Fallo (Hard Limit) |
|:---|:---|:---|
| **Hot Resume (Enjambre L1)** | Sub-10 ms | Pérdida de IPC Zero-Copy |
| **Warm Resume (Extracción L2)** | p95 < 200 ms | Base vectorial no indexada (Index Miss) |
| **Loop Cognitivo Local** | < 10 ms IPC / overhead | Cuello de botella en JSON (Prohibido) |
| **Adjudicación Profunda** | < 45 s resolución LogOP | Divergencia bizantina sin cierre |

---

## 13. Roadmap

| Fase | Hito Técnico y Entregable |
|:---|:---|
| **Fase 1: Hipervisor Cognitivo Core** | Modelado Rust de `BeliefObject`, ATMS DAG básico, criptografía en hojas (SMT) |
| **Fase 2: Sincronización de Enjambre** | Zenoh Pub/Sub, CRDTs Semánticos, Fusión LogOP |
| **Fase 3: Auditoría y Compliance** | EU AI Act (Art. 12) trazabilidad, exportación JSON-LD para auditores |
| **Fase 4: Consolidación Termodinámica**| Purga de Episodios, destilación axiomática en `NightShift` |

---

*Cortex-Persist · Whitepaper v0.2 · 2026-03-14*
*Author: Borja Moskv · License: Apache 2.0*
