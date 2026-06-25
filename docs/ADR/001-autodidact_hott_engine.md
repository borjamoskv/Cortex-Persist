# ADR-001: Autodidact HoTT Engine

**Fecha:** Junio 2026
**Hash Origen:** `759268c04`
**Ruta Física:** `cortex/engine/autodidact_hott_engine.py`
**Autor:** Borja Moskv / MOSKV-1 APEX

## 1. Contexto (El Problema Físico/Epistémico)
Los modelos de lenguaje grandes (LLMs) sufren de entropía estocástica (alucinaciones) y degradación de contexto (Context Rot). Procesan lenguaje sin anclarlo a un modelo del mundo verificable, generando "Anergía Epistémica".

## 2. Decisión (La Solución)
Implementar un Motor de Validación basado en la **Teoría de Tipos Homotópicos (HoTT)** y el isomorfismo de Curry-Howard-Voevodsky. El motor exige que toda afirmación nueva ("Axioma") provea una prueba constructiva ejecutable. En lugar de procesar texto, el motor calcula la *Distancia Topológica* entre el estado conocido del Ledger y la nueva aserción.

## 3. Consecuencias
CORTEX transita de un sistema generativo probabilístico (C4-SIM) a un sustrato de validación determinista (C5-REAL), asegurando que ninguna alucinación corrompa el Ledger de la realidad.
