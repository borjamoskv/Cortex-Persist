# Execution Model Specification

## 1. Definición Formal
El Modelo de Ejecución de CORTEX-PERSIST instaura un límite bizantino ("Byzantine Boundary") entre la capa estocástica (Inferencia de LLM) y la capa física determinista (Persistencia y Verificación Criptográfica).

## 2. Invariantes
- **Conjetura Generativa**: Ninguna salida generativa muta el estado sin atravesar las SMT Guards (Z3).
- **Prohibición de Bypass**: El `Write-Path Contract` (Saga-Pattern) no puede ser eludido. Si Z3 evalúa a `UNSAT`, la mutación es abortada térmicamente.

## 3. Arquitectura de Transición de Estado
La máquina de estado obedece el siguiente isomorfismo:
$$ State_{t+1} = MetaArbiter(Z3\_Validate(LLM(State_t))) $$

## 4. Complejidad
- La complejidad temporal depende estrictamente del Solver Z3 y del volumen de inferencia. La capa de persistencia promete latencias sub-milisegundo una vez que Z3 emite `SAT`.

## 5. Modos de Fallo
- **SMT Timeout**: Z3 es incapaz de decidir si las restricciones son satisfacibles dentro de un umbral temporal ($T_{max}$).
  - Resultado: Tratado implícitamente como `UNSAT`. Rollback inmediato.

## 6. Pruebas Asociadas
- `proofs/tests/z3_reject_invalid_transition.rs`
- `proofs/tests/z3_timeout.rs`
