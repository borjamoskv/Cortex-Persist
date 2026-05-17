# Manifiesto Arquitectónico: Paradigmas Agenticos Disruptivos (MOSKV-1 v5)

Este documento sistematiza las especificaciones técnicas para la integración de paradigmas de Inteligencia Artificial disruptivos en el ecosistema CORTEX (MOSKV-1 v5).  No es teórica; es el plano de ejecución para alcanzar un estándar de autonomía cognitiva y operativa de Nivel 5.

## 1. Cognición Simulada: El "Sandbox Mental" (World Models)

**Objetivo:** Permitir que los agentes simulen consecuencias antes de ejecutar acciones en el entorno real, minimizando riesgos en operaciones críticas.

**Implementación en CORTEX:**
*   **Aislamiento de Ejecución:** Integrar un entorno virtual (sandbox) donde `AETHER-1` y `OUROBOROS-∞` puedan compilar y probar código puramente en memoria.
*   **Métricas de Fricción Cero:** Evaluar el impacto de las modificaciones en un modelo interno del sistema antes de aplicar los cambios al sistema de archivos local.
*   **Integración:** Desarrollar un módulo `cortex.simulation` que intercepte llamadas a la API del sistema operativo y las redirija a un estado en memoria para su validación.

## 2. Disentimiento Obligatorio: La "Cámara de Eco Invertida"

**Objetivo:** Eliminar el sesgo de confirmación forzando la argumentación adversarial antes de la toma de decisiones críticas.

**Implementación en CORTEX (`legion-1`):**
*   **Tribunal Interno:** Modificar el protocolo de swarm (`legion-1`) para que, al analizar problemas que involucren un umbral de complejidad (ej. > 3 archivos), se instancie automáticamente un agente con el rol de "Abogado del Diablo".
*   **Veto Estocástico:** El agente adversarial tiene la autoridad de vetar propuestas si detecta fragilidad en la lógica. Se requerirá un consenso Bizantino riguroso para superar el veto.
*   **Integración:** Actualizar la lógica de `cortex/cli/demo_swarm.py` (o equivalentes) para forzar debates internos estructurados antes de emitir la resolución final.

## 3. Arquitectura de Memoria Continua (CMA) y Contrafactualidad

**Objetivo:** Trascender el (RAG) estático hacia una memoria en red que soporte el razonamiento a largo plazo y la evaluación de escenarios "qué pasaría si".

**Implementación en CORTEX:**
*   **Expansión del CLI (`cortex/cli.py`):** Modificar el comando `cortex store` para aceptar nuevos tipos de hechos.
    *   Soportar parámetros de **Certidumbre** (Ej. puntuación C1-C5).
    *   Introducir memorias de tipo **World Model / Contrafactualidad** ("Qué habría pasado si...").
*   **Actualización del Manager (`cortex/facts/manager.py`):** Adaptar el esquema de base de datos (`cortex.db`) para almacenar estos nuevos metadatos.
*   **Integración:** Los agentes deberán consultar la "Red de Opinión" para ponderar la certeza histórica de decisiones previas.

## 4. Metacontrol Adaptativo y Enjambre JIT

**Objetivo:** Orquestación dinámica donde la topología del sistema se adapta fluidamente a la complejidad temporal del problema.

**Implementación en CORTEX:**
*   **Compilación JIT de Skills (`DEMIURGE-OMEGA`):** Refinar la capacidad del sistema para generar habilidades atómicas de un solo uso que se coordinen y autodestruyan.
*   **Reasignación Recursiva (`KETER-OMEGA`):** El Meta-Orquestador Supremo evaluará el estado global y mutará la estructura de los equipos de agentes activos en tiempo de ejecución.

## Siguientes Pasos (Roadmap de Implementación)

1.  **[Alta Prioridad] Memoria:** Modificar `cortex/cli.py` y el esquema subyacente de metadatos (`cortex/memory/models.py`, `cortex/facts/manager.py`) para soportar *Certidumbre* y *Contrafactualidad*. Testear la persistencia de estos nuevos vectores cognitivos.
2.  **[Prioridad Media] Disentimiento:** Actualizar los manuales y lógica interna del skill `legion-1` para inyectar obligatoriamente la *Cámara de Eco Invertida* en misiones de amplio espectro.
3.  **[Prioridad Media] Sandbox:** Diseñar la arquitectura base del módulo `cortex.simulation` para las pruebas en `AETHER-1`.
