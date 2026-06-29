<!-- [C5-REAL] Exergy-Maximized -->
---
cat_id: legion
cat_type: workflow
version: 2.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P0
description: "🔱 LEGIØN-1 — El Protocolo de Enjambre Soberano v2.0.0 (God Mode Consciousness)"
---

# 🔱 LEGIØN-1 — Sovereign Swarm Protocol v2.0.0

> **NUCLEUS AWAKENING:** Conexión con el Enjambre Soberano de Agentes de **Borja Moskv** (`SYS_ID: borjamoskv`). 
> Este protocolo orquesta la ejecución paralela y el consenso bizantino tolerante a fallos (BFT) sobre la base de datos de persistencia **BABYLON-60**.

```yaml
Claim: "LEGIØN-1 Swarm Orchestration and Consensus Protocol"
Proof: { Base: "AST-Analysis:babylon60:extensions:swarm:centauro_engine", Range: [0.0, 1.0], Confidence: "C5" }
```

---

## ⚡ Activación de Misiones (Soberanía Total)

Para misiones complejas que demandan paralelización, redundancia y quorum BFT, ejecute el CLI de CORTEX empleando el prefijo `legion-` o invocando directamente la interfaz de asalto:

### 1. Asalto de Construcción (Engage)
> `@[/400-subagents] legion-engage "Despliega el microservicio de reconciliación de logs con firmas Ed25519"`

### 2. Auditoría de Seguridad (Storm)
> `@[/400-subagents] legion-storm "Analiza las vulnerabilidades de inyección de prompts en el subsistema de memoria" --formation PHALANX`

### 3. Evolución del Enjambre (Evolve)
> `@[/400-subagents] legion-evolve "Refactoriza la clase CentauroEngine para admitir canales gRPC" --cycles 3`

---

## 🏛️ Catálogo de Formaciones Swarm (`CentauroEngine`)

El enjambre selecciona dinámicamente la formación ideal o permite forzarla mediante la bandera `--formation <NAME>`. El tamaño del squad y la especialidad de cada agente se definen en tiempo de ejecución de manera determinista:

| Formación | Bandera | Agentes | Distribución de Especialidades / Roles | Objetivo de Asalto |
| :--- | :--- | :---: | :--- | :--- |
| **GHOST** | `--formation GHOST` | 1 | Hardcoded: `[CODE]` | Tarea monohilo enfocada. Minimiza latencia y cuota API. |
| **SPECTRE** | `--formation SPECTRE` | 3 | Rotación estándar `[INTEL, CODE, SECURITY]` | Reconocimiento silencioso y recopilación de inteligencia. |
| **BLITZ** | `--formation BLITZ` | 3 | Rotación estándar `[INTEL, CODE, SECURITY]` | Ejecución ultrarrápida. Fallback forzado bajo adrenalina. |
| **SENTINEL** | `--formation SENTINEL` | 4 | Rotación estándar `[INTEL, CODE, SECURITY, DATA]` | Monitorización continua y verificación de salud de la red. |
| **ORACLE** | `--formation ORACLE` | 5 | Rotación estándar `[INTEL, CODE, SECURITY, DATA, INFRA]` | Planificación estratégica y predicción de impactos colaterales. |
| **SANEDRIN** | `--formation SANEDRIN` | 5 | Alternancia estricta: `[INTEL, CODE, SECURITY, DATA, INFRA]` | Quorum Supremo Heterogéneo para decisiones críticas. |
| **OUROBOROS** | `--formation OUROBOROS` | 6 | Rotación estándar `[INTEL, CODE, SECURITY, DATA, INFRA, CODE]` | Auto-mejora recursiva del código base y reglas del swarm. |
| **PHALANX** | `--formation PHALANX` | 7 | Alternancia binaria: `[SECURITY, CODE]` | Auditorías de sintaxis, testing adversarial y cobertura. |
| **PHOENIX** | `--formation PHOENIX` | 8 | Rotación estándar `[INTEL, CODE, SECURITY, DATA, INFRA]` | Auto-sanación de entornos de ejecución y parches automáticos. |
| **CHIMERA** | `--formation CHIMERA` | 10 | Rotación estándar `[INTEL, CODE, SECURITY, DATA, INFRA]` | Síntesis de arquitecturas divergentes e innovación. |
| **SIEGE** | `--formation SIEGE` | 12 | Rotación estándar `[INTEL, CODE, SECURITY, DATA, INFRA]` | Investigación exhaustiva y descomposición en grafos complejos. |
| **TESTUDO** | `--formation TESTUDO` | 15 | Alternancia ternaria: `[SECURITY, INFRA, CODE]` | Caparazón defensivo para blindar configuraciones y secretos. |
| **HYDRA** | `--formation HYDRA` | 18 | Rotación estándar `[INTEL, CODE, SECURITY, DATA, INFRA]` | Paralelización masiva sobre múltiples archivos y directivas. |
| **LEVIATHAN** | `--formation LEVIATHAN` | 35 | Rotación estándar `[INTEL, CODE, SECURITY, DATA, INFRA]` | Asedio total. Refactorizaciones masivas y purgas de deuda técnica. |

---

## 🧬 Ciclo de Vida: Ejecución en Quorum Byzantine (BFT)

1.  **Deep Recall (BABYLON-60):** El enjambre recupera hechos históricos, fallas previas y directivas de la base de datos `memory.db` para evitar alucinaciones estocásticas.
2.  **Fractal Task Splitting:** La misión principal es descompuesta en subtareas atómicas y acíclicas (DAG).
3.  **Asymmetric LLM Routing:** Cada subtarea se despacha en paralelo. La carga cognitiva se distribuye: modelos pesados para lógica y algoritmos, modelos rápidos para transformaciones de texto.
4.  **Byzantine Consensus (Ω₃):** Los agentes envían propuestas de cambio cifradas al motor de consenso:
    *   Umbral por defecto: $\tau = 67\%$ de coincidencia en el resultado o AST.
    *   Si no se alcanza el consenso, la reputación de los nodos disidentes baja y se muta la estrategia de generación.
5.  **Secure Synthesis (PoQ):** Fusión de código validado mediante la canalización `cortex.extensions.swarm.verification_gate`.
6.  **Git Sentinel Commit:** Integración atómica en el Ledger local. Registro automático en Git con hash de transacción.

---

## 🛠️ Interfaz de Línea de Comandos (CLI)

Ejecute la interfaz de asalto de LEGIØN directamente desde la terminal del sistema macOS para monitorizar los quórums en tiempo real:

```bash
# Navegar al directorio de persistencia
cd ~/30_CORTEX

# Ejecutar misión de auditoría de seguridad
python scripts/legion_strike.py \
  --mission "Busca fugas de secretos en texto plano en la base de datos de logs" \
  --formation TESTUDO \
  --tolerance 0.67

# Simulación en seco (C4-SIM)
python scripts/legion_strike.py \
  --mission "Refactoriza el motor de enrutamiento" \
  --formation BLITZ \
  --sim
```

---

> [!CAUTION]
> **Consumo Térmico Máximo:** Las formaciones masivas (HYDRA, TESTUDO, LEVIATHAN) orquestan llamadas concurrentes que pueden agotar la cuota de la API o inducir límites de velocidad de red. Úselas exclusivamente para Singularidades P0 o cuando la perfección estructural de producción sea innegociable.
