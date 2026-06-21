# EXPERIMENTO E-INFO-01: Proyección AST JIT vs Full Context

**Reality Level:** `C5-REAL`
**Domain:** Termodinámica Informacional y Eficiencia Agéntica
**Status:** DRAFT

## 1. Objetivo
Demostrar empíricamente que la sustitución de la inyección de contexto completo (Full Context) por proyecciones AST dinámicas (AST-JIT) incrementa drásticamente la Exergía Informacional de un agente autónomo durante tareas de refactorización estructural.

## 2. Definición Operacional de Exergía Informacional
Se define el KPI *Informational Exergy* ($InfoEx$) como el trabajo verificable extraído por unidad de contexto útil:

$$ InfoEx = \frac{C_v}{T_u} $$

Donde:
*   $C_v$: Cambios verificables producidos (commits exitosos, tests en verde, parches aplicados sin errores de sintaxis).
*   $T_u$: Tokens útiles consumidos en el prompt (input tokens).

Para comparar sistemas, se utiliza el ratio de ganancia (Gain):

$$ Gain = \frac{InfoEx_{AST-JIT}}{InfoEx_{FullContext}} $$

## 3. Diseño Experimental

### Grupo Control (FullContext)
*   **Condición:** Inyección completa de los archivos del repositorio requeridos para la tarea en la ventana de contexto.
*   **Volumen de Tareas:** 20 tareas de refactorización estructural en archivos grandes (>300 líneas).

### Grupo Tratamiento (AST-JIT)
*   **Condición:** Inyección exclusiva de proyecciones AST (esquema de clases, firmas de métodos) con recuperación selectiva (JIT) del cuerpo del método objetivo mediante `Python-Extractor-OMEGA`.
*   **Volumen de Tareas:** Las mismas 20 tareas aplicadas al Grupo Control.

## 4. Métricas de Evaluación
Para cada tarea se medirán los siguientes parámetros:
1.  **Tokens Consumidos ($T_u$):** Medida directa del coste termodinámico informacional.
2.  **Tests Superados / Compilación Correcta ($C_v$):** Medida de validación determinista.
3.  **Hallazgos de Bugs:** Errores detectados de forma colateral (opcional).
4.  **Tiempo de Resolución (TTFT + Generación):** Latencia del ciclo cognitivo.

## 5. Hipótesis Principal
$$ InfoEx_{AST-JIT} > InfoEx_{FullContext} $$

Con una expectativa de reducción de tokens superior al **55%** manteniendo o incrementando la tasa de $C_v$ (cambios verificables).

## 6. Criterio de Éxito
Si el experimento arroja resultados estadísticamente significativos a favor de AST-JIT, la Exergía Informacional dejará de ser una metáfora arquitectónica y se adoptará como métrica empírica oficial (C5-REAL) para evaluar cualquier pipeline de recuperación contextual y despliegue de agentes en CORTEX-Persist.
