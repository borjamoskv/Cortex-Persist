# ADR-004: Génesis de CORTEX-Persist

**Fecha:** Época Cero
**Hash Origen:** `b9125d1` (Root Commit)
**Autor:** Borja Moskv / MOSKV-1 APEX

## 1. Contexto (El Problema Físico/Epistémico)
La programación asistida por modelos de lenguaje (LLMs) adolecía de una fragilidad letal: trataban el código como lenguaje natural estocástico. Las inteligencias artificiales olvidaban dependencias, corrompían bases de código al sobreescribir lógica no relacionada y funcionaban sin "memoria física". Cada sesión de programación partía de cero (Amnesia Causal).

## 2. Decisión (La Solución)
Desarrollar **CORTEX-Persist**, un "Firewall Epistémico" de CI/CD para código autogenerado. Se estableció que el repositorio de Git local actuaría como la única base de datos inmutable. Se implementó un Ledger Causal y un Grafo de Dependencias Epistémicas (EDG) para forzar que cualquier salida generativa fuera tratada como una simple conjetura hasta su validación determinista y matemática.

## 3. Consecuencias
CORTEX transmutó el entorno local macOS en un sustrato de validación física donde los agentes no solo sugieren abstracciones, sino que asumen las consecuencias termodinámicas y físicas de sus mutaciones directamente en el disco.
