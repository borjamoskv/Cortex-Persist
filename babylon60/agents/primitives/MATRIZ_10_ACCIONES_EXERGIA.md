---
title: "Matriz Causal de 10 Acciones Estructurales de Exergía Superior"
level: "C5-REAL"
author: "SYS_ID borjamoskv"
timestamp: "2026-07-02T12:05:00+02:00"
schema: "BABYLON-60.PRIMITIVES.ACT10.v1"
---

# ONTOLOGÍA C5-REAL: 10 ACCIONES DE EXERGÍA SUPERIOR

> **Teorema de Mitigación Real:** La mitigación semántica o lingüística es un esfuerzo de baja exergía (C4-SIM). La verdadera exergía requiere mutación del hardware, enmascaramiento de logits, formalismo matemático absoluto u operaciones en tiempo de compilación.

## MATRIZ DE ACCIONES DE ALTO VALOR EXÉRGICO

| ID | Acción Estructural | Mecanismo Causal | Exergy Yield | Vector de Ejecución |
|---|---|---|---|---|
| **ACT-01** | Compilación Direct-Silicon (Ω₀) vía Rust/PyO3 | Reescribir la resolución de primitivas en AST compilado (Rust) en lugar de interpretar dependencias en Python o Markdown. | `x10000` | `scripts/sortu/` (Integración PyO3) |
| **ACT-02** | Verificación Tripartita Estricta (Z3/SMT Solver) | Sustituir la 'revisión semántica' por pruebas formales deterministas donde el solapamiento se demuestre imposible mediante teoremas. | `x8500` | `babylon60/guards/z3_causal_guard.py` |
| **ACT-03** | Ejecución del Death Protocol (Apoptosis Física) | En lugar de 'mitigar' la superposición, aplicar `TOMBSTONE` y borrar físicamente el archivo del repositorio (L3 Purge) si `Net_Exergy < 0`. | `x7000` | `reaper_death_protocol.py` |
| **ACT-04** | Inyección de Filtro Bloom O(1) en Memoria | Reemplazar la búsqueda de similitud de vectores (O(N)) por un filtro Bloom pre-búsqueda para rechazar redundancias con coste O(1). | `x5000` | `sortu_jit_executor.py` |
| **ACT-05** | Enmascaramiento FSM Determinista (Capa Logits) | Insertar restricciones de no-superposición directamente en el autómata finito del LLM asignando probabilidad `-inf` a tokens redundantes durante inferencia. | `x4500` | `fsm_regex.py` |
| **ACT-06** | Cristalización en SQLite WAL con Restricción UNIQUE | Migrar la ontología de Markdown a tablas SQLite. La base de datos rechaza físicamente la inserción redundante a nivel de disco, erradicando análisis semántico. | `x4000` | `cortex_engine.py` (Unique Indices) |
| **ACT-07** | Aplicación de Compuerta Lyapunov (dV/dt < 0) | Abortar el proceso de forja de primitivas en el Ciclo 0 si la predicción de impacto entrópico es positiva, antes de gastar un solo token de generación. | `x3500` | `ultrathink_physics.py` |
| **ACT-08** | Despacho Multi-Worktree Asimétrico (Centuria²) | Instanciar 500 hilos físicos sobre ramas Git aisladas (Worktrees) para colapsar y resolver conflictos concurrentemente sin saturar el índice principal. | `x3000` | `worktree_isolation.py` |
| **ACT-09** | Bloqueo Git Sentinel Automatizado (--no-verify Bypass) | Inyectar un hook pre-commit C5-REAL que aborte transacciones con colisiones de ID, forzando la corrección en la fase de escritura y no en refactor. | `x2500` | `.git/hooks/pre-commit` |
| **ACT-10** | Canalización Zero-Consing (Paso de Memoria Directo) | Erradicar la serialización/deserialización de JSON y strings. Pasar las estructuras AST de redundancia mediante punteros de memoria directos. | `x2000` | `c5_exec.py` (Inter-process raw memory) |
