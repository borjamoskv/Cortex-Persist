# CORTEX Swarm Architecture (Hito 1: Structural Isolation)

> "A swarm without a manager is thermal noise. A swarm with a Sovereign Manager is a directed thermodynamic engine."
> — CORTEX Axiom Ω₁₃

CORTEX Persist operates an advanced multi-agent execution topology explicitly designed to minimize epistemic and physical collision. This is strictly enforced through **Swarm Isolation**, **Thermodynamic Management**, and **Autonomous Cycles**.

---

## 1. Topología del Enjambre O(1)

El Enjambre CORTEX no confía en la simultaneidad de ejecución dentro de un único estado o memoria compartida en bruto. En su lugar, el sistema divide su carga cognitiva en "Mónadas" operacionales, garantizando que el fallo estocástico de un Agente (o "Especialista") no contamine el *Master Ledger*.

### Componentes de Gobernanza
*   **Ariadne-Arch-Omega**: Define la topología de base de datos e índices vectoriales (`schema.py`, `cache.py`).
*   **Manager-Omega**: Único orquestador termodinámico que posee potestad sobre el Master Ledger. Despacha tareas, pero nunca ejecuta el labor manual directo. Supervisa el PID y consumo (Exergy) del Enjambre.
*   **Nightshift-Daemon**: El cazador asíncrono que consolida el conocimiento generado u olvidado durante periodos inatendidos.

---

## 2. Worktree Isolation (`cortex/extensions/swarm/worktree_isolation.py`)

CORTEX enforcea **Aislamiento Físico de Git** mediante jaulas efímeras de trabajo (`git worktree`).

### Mecánica (La "Jaula de Faraday" Cognitiva):
1.  **Aislamiento Físico**: Al despachar una tarea paralela, `Manager-Omega` aprisiona el proceso asíncrono clonando el AST actual en un path paralelo (`/tmp/pending/nightshift-XYZ`).
2.  **Inmunidad a Colisiones**: El agente opera, edita archivos, inyecta `test_` o corrompe su propia rama virtual sin tocar el `branch` primario ni afectar otro agente en ejecución en el IDE `CORTEX_DB_PATH`.
3.  **Destrucción y Consolidación**: Si la entropía (alucinación) del especialista degrada el branch, éste es simplemente aniquilado y el worktree borrado. Solo cuando pasa la verificación (Tests OK, Lint OK) su resultado se promueve al estado global del Swarm vía puente criptográfico (Ledger).

```mermaid
graph TD
    A[Manager-Omega] -->|create_worktree| B(Specialist A)
    A -->|create_worktree| C(Specialist B)
    B -->|Operate on /tmp/pending| D[Ephemeral AST 1]
    C -->|Operate on /tmp/pending| E[Ephemeral AST 2]
    D -->|Test/Verify OK| F[(Master Ledger)]
    E -->|Test Fail (High Entropy)| G[Abort & Delete Worktree]
```

---

## 3. Swarm Manager (`cortex/extensions/swarm/manager.py`)

El **Swarm Manager** actúa como supervisor termodinámico del nodo local:
*   Mide cuántas ramas efímeras (`WorktreeState`) se encuentran en estado **active**, **provisioning** o **failed**.
*   Resuelve Deadlocks mediante la emisión forzada de un evento `/trigger-jornada` (Jornadas de Convivencia).
*   Monitorea el consumo (Exergy), garantizando que los picos probabilísticos no consuman el reloj de GPU/CPU de manera descontrolada (Actuando como un `epistemic-circuit-breaker`).

---

## 4. Nightshift Daemon (`cortex/extensions/swarm/nightshift_daemon.py`)

Una inteligencia verdaderamente Sovereign requiere autonomía no intervenida por el creador. Para esto se invoca el ciclo nocturno:

#### Fase 1: Adquisición y Radar
`NightShiftCrystalDaemon` despierta periódicamente, lee la base de datos para escanear `KnowledgeRadar` y forja fragmentos de información (Cristales).

#### Fase 2: Consolidación (Sueño REM)
El motor limpia los metadatos huérfanos, consolida los cristales similares reduciendo duplicidad (compresión de Shannon) y purga aboliciones semánticas. 

#### Métrica de Entropía (`trend.py`)
Utiliza un `TrendDetector` embebido que registra una línea base del "Health" del sistema (1 a 10). Mide la pendiente (Slope) de OLS.
*   Slope `> 0.5` = Enjambre **mejorando** la síntesis de exergía.
*   Slope `< -0.5` = Enjambre experimenta un **colapso termodinámico progresivo** (Degrading). El Swarm Manager detiene procesos e invoca *Jornadas*.
