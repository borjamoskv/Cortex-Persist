---
description: Cortex-Persist Whitepaper v0.2.2 — Infraestructura de gobernanza cognitiva para enjambres de agentes
---

# Cortex-Persist

## Infraestructura de gobernanza cognitiva para continuidad de memoria, resolución de colisiones y consistencia operacional en enjambres de agentes autónomos

---

## 0. Estado

**Normative Draft v0.2.2** — 2026-03-14

> **Normative Bridge:** Este documento es descriptivo. Cualquier interpretación a nivel de requisitos DEBE referirse al RFC-CORTEX-NATIVE-AI v0.1 y sus sucesores.

---

## 1. Resumen ejecutivo

Cortex-Persist define una arquitectura de gobernanza cognitiva para sistemas multi-agente de larga duración. Su objetivo es mantener estado de creencias revisable, trazable y operacionalmente admisible bajo concurrencia, conflicto y degradación temporal.

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

## 3. Definiciones operativas

Para anclar el modelo, Cortex-Persist emplea la siguiente semántica:

- **Belief Object (BO)**: Unidad estructurada de estado cognitivo operacional. Un BO representa una proposición junto con su procedencia, confianza, incertidumbre, relaciones lógicas, política temporal y estado epistémico. No es texto recuperado por similitud; es memoria gobernable. (Ver Apéndice A).
- **Entropía Cognitiva**: La acumulación de ruido semántico, recuerdos obsoletos y creencias contradictorias que degrada la precisión inferencial de un agente con el tiempo.
- **Admisibilidad Epistémica**: Condición bajo la cual una afirmación (incluso si está criptográficamente íntegra) es válida para ser inyectada en el prompt, basada en su soporte de evidencia y ausencia de colisión irresoluble.
- **Contaminación Estructural**: Propagación de fallos lógicos a través del grafo de dependencias, donde el colapso de una premisa raíz invalida silenciosamente cientos de inferencias derivadas.
- **Colisión Semántica**: Concurrencia de Belief Objects con proposiciones lógicamente excluyentes sobre el mismo dominio de estado.
- **Scheduler Risk / Risk_contam**: Riesgo cuantificado por el programador de memoria de inyectar contexto estructuralmente contaminado en la ventana de inferencia del LLM.

---

## 4. Objetivos y no-objetivos

### No-objetivos

Cortex-Persist no garantiza:

- Verdad objetiva del mundo,
- Satisfacibilidad lógica global en tiempo de ingestión,
- Consenso bizantino en redes arbitrariamente hostiles,
- Latencia constante bajo cualquier carga,
- Borrado semántico de salidas ya expuestas a terceros modelos.

---

## 5. Modelo del sistema

El sistema opera como un hipervisor cognitivo descentralizado estructurado en tres planos formales:

1. **Plano de Creencias:** Gestiona los *Belief Objects*, la máquina de estados y el mantenimiento de la verdad basado en suposiciones (ATMS).
2. **Plano de Integridad:** Garantiza la inmutabilidad y procedencia mediante Sparse Merkle Trees (SMT) y firmas criptográficas.
3. **Plano de Coordinación:** Orquesta la propagación de estado a través del enjambre mediante CRDTs semánticos, resolviendo colisiones con algoritmos de consenso bayesiano (LogOP).

Los agentes producen hechos. El *Memory Scheduler* dicta la inyección de contexto. El protocolo de consenso propaga los estados. La memoria compartida (iceoryx2) provee IPC lock-free hacia los pipelines inferenciales.

---

## 6. Separación explícita: Integridad vs. Validez vs. Utilidad

Cortex-Persist disocia formalmente tres propiedades que las arquitecturas RAG ingenuas confunden en la etapa de recuperación:

- **Integridad**: Garantiza que el evento, parche o artefacto no ha sido alterado y mantiene continuidad criptográfica y de procedencia.
- **Validez epistémica**: Determina si una creencia sigue siendo admisible bajo evidencia, conflicto, dependencia y política.
- **Utilidad operacional**: Determina si esa creencia merece ocupar contexto inferencial en una tarea y momento concretos.

La integridad es garantizada en anillo cero. La validez epistémica se calcula por la topología del grafo en la ingesta y revisión. La utilidad operacional es gobernada JIT por el Memory Scheduler.

---

## 7. Gobernanza cognitiva

Si la memoria se gobierna, el conocimiento se limpia.

Cuando entra una pieza de evidencia que contradice una creencia activa, Cortex-Persist no la sobreescribe (sobrescribir destruye el linaje) ni promedia los vectores (eso crea amalgamas sin sentido).

El sistema:
1. Pasa el estado de la creencia a `Contested`.
2. Activa una revisión bayesiana para recalibrar el `confidence_score`.
3. Propaga la invalidación con coste acotado por el subgrafo dependiente, usando índices estructurales para acceso constante a las dependencias directas a través del ATMS.

Ninguna creencia vive sola. Si cae el cimiento, cae la estructura subordinada de inferencias en cascada, según la tabla de transiciones formales (Ver Apéndice A).

---

## 8. Swarm Sync y resolución de conflictos

Sincronizar cien agentes autónomos requiere convergencia matemática. El sistema emplea **CRDTs Semánticos** (Tipos de Datos Replicados Libres de Conflictos). 

A diferencia de los CRDTs estándar basados en el reloj del sistema (LWW - Last Writer Wins), el modelo de Cortex prioriza la causalidad lógica. LWW es peligroso en sistemas cognitivos: un reloj más reciente no hace que un argumento sea más válido.

Si dos agentes divergen fuertemente:
- Se invoca la capa de consenso (LogOP - Logarithmic Opinion Pool).
- Los vetos aplican una penalización epistémica saturante.
- La retirada de soporte operativo o deactivación de un consenso requiere superar un umbral predefinido (*consensus collapse threshold*) o el requisito de auditoría definido por política. 

CRDTs proporcionan convergencia estructural de réplicas y causalidad operativa suficiente para propagación distribuida. No determinan por sí mismos superioridad evidencial ni corrección semántica. La resolución epistémica ocurre por encima de la capa de réplica.

---

## 9. Invariantes del Sistema

Cortex-Persist opera bajo los siguientes invariantes axiomáticos:

1. Ningún `BeliefObject` cambia de estado sin un evento trazable.
2. Ninguna invalidación destruye el linaje histórico.
3. Ningún nodo único puede retirar soporte operativo compartido por encima del umbral de política.
4. La integridad criptográfica no implica validez epistémica.
5. La convergencia de réplica no implica corrección epistémica.

---

## 10. Memory Scheduler

El programador de memoria evalúa una ecuación tensorial en cada ciclo de inferencia. Calcula un puntaje explícito para decidir qué Belief Objects se inyectan en el prompt:

$$ \text{Score}(m) = \frac{(\text{Rel} \cdot w_r) + (\text{Conf} \cdot w_c) + (\text{Rec} \cdot w_t)}{\text{Cost}_{\text{tokens}} + \text{Risk}_{\text{contam}}} $$

Bajo esta mecánica, el scheduler puede excluir completamente el objeto de la inyección contextual cuando el riesgo de contaminación estructural supera el umbral operativo, marginando datos que aunque semánticamente similares a la consulta, sufren patologías en sus dependencias.

---

## 11. Integrity & Provenance

*Fronteras de confianza*

Una firma válida autentica autoría, no veracidad.
Una procedencia verificable no implica que el contenido sea correcto.
La activación de una creencia requiere más que integridad criptográfica: requiere admisibilidad epistémica bajo contexto, fuente y conflicto.

El linaje criptográfico es innegable. Todo cambio de estado, parche semántico o actualización de linaje es un evento sellado en un Sparse Merkle Tree (SMT). Se puede generar una prueba verificable del linaje de los artefactos, estados y transiciones que contribuyeron a una conclusión operacional del enjambre.

---

## 12. Target Engineering Goals (SLOs Provisionales)

> **Nota Epistémica:** Estos objetivos (_non-binding provisional performance targets_) requieren validación empírica continua mediante ENCB y profiling de implementación nativa. Sujeto a benchmark reproducible.

| Operación | TARGET Operativo Provisional | Condición de Fallo (Hard Limit) |
|:---|:---|:---|
| **Hot Resume (Enjambre L1)** | Sub-10 ms | Pérdida de IPC Zero-Copy |
| **Warm Resume (Extracción L2)** | p95 < 200 ms | Base vectorial no indexada (Index Miss) |
| **Loop Cognitivo Local** | < 10 ms IPC / overhead | Uso de JSON intermedio (En critical path) |
| **Adjudicación Profunda** | < 45 s resolución LogOP | Divergencia bizantina sin cierre |

---

## 13. Roadmap

| Fase | Hito Técnico y Entregable |
|:---|:---|
| **Fase 1: Hipervisor Cognitivo Core** | Modelado Rust de `BeliefObject`, ATMS DAG básico, criptografía en hojas (SMT) |
| **Fase 2: Sincronización de Enjambre** | Zenoh Pub/Sub, CRDTs Semánticos, Fusión LogOP |
| **Fase 3: Auditoría y Compliance** | EU AI Act (Art. 12) trazabilidad, JSON-LD, Appendix B Threat Model mitigations |
| **Fase 4: Consolidación Termodinámica**| Purga de Episodios, destilación axiomática en `NightShift` |

---

## Apéndices

### Appendix A — Belief Object Schema & State Transitions

La unidad atómica representable en Rust evita la deriva ontológica tipando estáticamente la proposición:

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
    pub source_type: String, // agent, tool, human
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
pub enum PropositionPayload {
    Boolean(bool),
    Categorical(String),
    Scalar(f64),
    Set(Vec<String>),
    Reference { uri: String, kind: String },
}

#[derive(Debug, Clone)]
pub struct BeliefObject {
    pub id: uuid::Uuid,
    pub proposition_key: String,
    pub payload: PropositionPayload,
    pub confidence_score: f32,
    pub uncertainty: f32,
    pub decay_rate: f32,
    pub state: BeliefState,
    pub provenance: ProvenanceEnvelope,
    pub relations: Vec<BeliefRelation>,
    pub timestamp_created: i64,
    pub timestamp_last_verified: i64,
    pub semantic_version: u32,
}
```

**State Transitions**

| From | Trigger | To |
|:---|:---|:---|
| Active | conflicting evidence | Contested |
| Active | strong refutation | Discarded |
| Active | superseded revision | Subsumed |
| Contested | resolved positive | Active |
| Contested | resolved negative | Discarded |
| Subsumed | retention policy | Archived |
| Discarded | retention policy | Archived |

### Appendix B — Threat Assumptions

| Amenaza | Capa | Impacto | Defensa |
|:---|:---|:---|:---|
| **Agente honesto pero falible** | Belief | Medio | recalibración de confianza + trazabilidad |
| **Agente malicioso con firma válida** | Integrity/Belief | Alto | integridad $\neq$ admisibilidad + cuarentena |
| **Replay patch** | Sync | Alto | causalidad monótona + supresión de duplicados |
| **Colusión de agentes** | Swarm | Alto | diversidad + detección de anomalías |
| **Compromiso de clave** | Integrity | Crítico | rotación + tenant scoping + revoke |
| **Partición de red** | Sync | Medio | convergencia eventual + reconciliación diferida |
| **Loop autoreferencial** | Scheduler/Belief| Alto | $Risk_{\text{contam}}$ + fork_memory |
| **Fuente formalmente correcta pero falsa** | Provenance/Belief| Alto | procedencia verificable + revisión epistémica |

### Appendix C — Evaluation Metrics

Cortex-Persist será evaluado empíricamente frente a sistemas de memoria pasiva (bases de datos vectoriales estándar) empleando el benchmark nativo **ENCB** *(Epistemic Noise Chaos Benchmark)*.

Se cuantifican cinco métricas primarias:
- **Persistent False Belief Rate**: Resistencia a la retención de hechos refutados por evidencia posterior.
- **Epistemic Debt Integral**: Acumulación temporal de contradicciones no resueltas en grafos operativas.
- **Recovery Round**: Cantidad de *turns* inferenciales o ciclos LogOP requeridos para alcanzar nuevo consenso tras un shock de partición.
- **Containment Latency**: Tiempo incurrido desde el fallo de una dependencia raíz hasta el colapso del estado en todo su vecindario subgrafo.
- **Structural Contradiction Mass**: Porcentaje de aserciones incompatibles extraídas concurrentemente durante un volcado de contexto.

**Baselines de validación estructural:**
- Sobrescritura ingenua de sumarios textuales.
- CRDT ciego sin modelado Bayesiano.
- LWW (Last Writer Wins) sobre bases vectoriales tradicionales.
- Cortex-Persist Full (LogOP + ATMS + Epoch SMT).

---

*Cortex-Persist · Whitepaper v0.2.2 · Autor: Borja Moskv · Licencia: Apache 2.0*
