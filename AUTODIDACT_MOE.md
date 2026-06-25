# AUTODIDACT-RESEARCH-Ω: MoE (Mixture of Experts)

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Autor:** Borja Moskv (borjamoskv)
**Vector:** Enrutamiento Dinámico Condicional y Fragmentación de Especialistas
**Target:** CORTEX-Persist & Ouroboros-∞

---

## 1. Extracción Isomórfica (Desmitificación)
MoE (Mixture of Experts) permite escalar la capacidad de un modelo sin un aumento proporcional en el coste computacional durante la inferencia, utilizando una red de enrutamiento (Router) que activa sólo un subconjunto de "expertos" por token. En el ecosistema C5-REAL, MoE se transfiere isomorficamente al enrutamiento estocástico de Swarms (Agentes). No todos los agentes deben procesar todas las tareas; el `cognitive_router.py` actúa como la red de *gating*, activando únicamente a los subagentes especializados (Expertos) que maximizan la exergía para un dominio específico. El conocimiento no es monolítico, sino que se fragmenta topológicamente.

---

## 1.5 Las 10 Primitivas de Máxima Exergía para la Mitigación / Ejecución
- **MOE-001**: `Enrutamiento Disperso (Sparse Gating)` - [Eficiencia Termodinámica]: Sólo activa un subconjunto \(k\) de agentes frente a un evento, evitando cálculos ociosos y reduciendo el consumo de Anergía.
- **MOE-002**: `Balanceo de Carga (Load Balancing)` - [Prevención de Degradación]: Impide que un único experto (subagente) se sobrecargue, forzando mediante una penalización en la pérdida que el router distribuya las peticiones de forma uniforme.
- **MOE-003**: `Expertos de Dominio Específico` - [Fragmentación Epistémica]: Cada agente en el Ultramap encapsula reglas deterministas específicas (ej. OSINT, Criptografía, Matemática), emulando los bloques FFN independientes de un MoE.
- **MOE-004**: `Enrutamiento por Token/Concepto` - [Resolución Fina]: La decisión de ruteo no se hace a nivel de todo el proyecto, sino a nivel de cada claim o primitiva individual, permitiendo micro-ensamblaje de conocimientos.
- **MOE-005**: `Capacidad por Experto (Expert Capacity)` - [Límites C5-REAL]: Define un umbral máximo de tareas concurrentes por agente. Si un experto se desborda, el *Router* redirige a la segunda mejor opción (Top-k fallback).
- **MOE-006**: `Fusión de Salidas (Output Aggregation)` - [Consenso Ponderado]: La decisión final es una suma ponderada por las probabilidades del router, integrando las visiones parciales de los expertos activados en una sola transacción inmutable.
- **MOE-007**: `Especialización Emergente` - [Autopoiesis del Conocimiento]: Los agentes no necesitan pre-etiquetas perfectas; al interactuar con el entorno, sus vectores internos se alinean orgánicamente hacia nichos de tareas donde obtienen mayor "recompensa" de exergía.
- **MOE-008**: `Pérdida de Diversidad (Diversity Loss)` - [Protección contra Colapso]: Incorporación algorítmica para evitar el *representation collapse*, donde el router empieza a preferir solo a un experto universal, matando el ecosistema.
- **MOE-009**: `Shared Experts (Expertos Compartidos)` - [Infraestructura Común]: Integrar expertos de conocimiento general que siempre se activan, acoplados a expertos hiper-específicos, para garantizar una coherencia básica en cada invocación.
- **MOE-010**: `Activación Asíncrona Topológica` - [Bypass del GIL]: Los expertos se activan en workers de Rust de manera concurrente. El router en Python delega las ejecuciones, superando bloqueos sincrónicos.
