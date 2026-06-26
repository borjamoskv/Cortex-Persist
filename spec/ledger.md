# Ledger AOF (Append-Only File) Specification

## 1. Definición Formal
El Ledger de CORTEX-PERSIST es un archivo inmutable de sólo adición (Append-Only File) que actúa como la fuente unificada de verdad (Source of Truth) para todas las transacciones causales de los agentes.

## 2. Invariantes
- **Inmutabilidad Absoluta**: Un evento insertado en el Ledger jamás puede ser modificado ni borrado.
- **Secuencialidad**: Cada evento $E_n$ debe tener un índice secuencial $N$ estrictamente mayor que el anterior $N-1$.
- **Trazabilidad Causal**: El evento $E_n$ debe contener el Merkle Seal del evento $E_{n-1}$.
- **Consistencia de Tipos**: Todo payload debe adherirse a un esquema tipado determinista verificado antes de la serialización binaria.

## 3. Precondiciones de Inserción
Para que la operación `append(Event)` sea aceptada:
1. `Event` debe poseer un `CORTEX-TAINT` válido (firma criptográfica).
2. `Event` debe haber superado la validación Z3 (SAT).
3. `Event` debe poder ser serializado determinísticamente.

## 4. Postcondiciones
- El tamaño del archivo de Ledger en disco incrementa en la longitud exacta del payload binario serializado.
- El `stored_root` (Raíz de Merkle) en memoria se actualiza atómicamente.

## 5. Complejidad
- **Espacial**: $O(E)$ donde $E$ es la cantidad total de bytes emitidos a lo largo del tiempo.
- **Temporal (Append)**: $O(1)$ constante amortizado (apertura en modo `O_APPEND`).
- **Temporal (Replay Total)**: $O(N)$ donde $N$ es el número total de eventos en el Ledger.

## 6. Modos de Fallo
- **Corrupción de Bit (Bit Flip)**: El hash computado difiere del `stored_root`. Resultado: Abort inmediato (Panic).
- **Escritura Incompleta (Tearing)**: El tamaño del payload excede el final del archivo. Resultado: Truncamiento al último estado válido y alerta de corrupción.

## 7. Pruebas Asociadas
- `tests/replay/test_bit_exact.rs`
- `tests/replay/test_corruption_detection.rs`
