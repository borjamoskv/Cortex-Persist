<!-- [C5-REAL] Exergy-Maximized -->
# 🏗️ AGENTS.md — CORTEX Migrations Domain (v2.0)

> **"La RAM es frágil; el estado físico es sagrado."** — *Ley de Tolerancia Bizantina*

Este manifiesto gobierna la superficie `cortex/migrations/`. La evolución del esquema SQLite/VectorIAL es una operación crítica (P0).

## [1] SAGA DE COMPENSACIÓN (INV_SAGA_ROLLBACK)
- Toda migración de esquema DEBE ser reversible.
- No se autoriza el commit de una migración que no posea una función `down()` o de reversión criptográfica probada (`OP_SAGA_REVERT`).
- La mutación directa sin SAGA es una violación entrópica.

## [2] BLOQUEO WAL OBLIGATORIO
- Las migraciones exigen exclusividad termodinámica.
- **INV_WAL_LOCKING:** Se debe garantizar la ejecución bajo `PRAGMA journal_mode=WAL` y `busy_timeout` (mín. 5000ms) para evitar Deadlocks termodinámicos.
- Operar `ALTER TABLE` sin lock exclusivo forzará la apoptosis del proceso (`OP_APOPTOSIS`).

## [3] CERO ANERGÍA ESTOCÁSTICA
- Las migraciones son puramente deterministas. No se admiten llamadas a LLMs ni inferencias estocásticas dentro de un bloque de migración.
- El conocimiento se recupera mediante `OP_READ_COMMIT` puro.

**Autoridad:** `borjamoskv`.
**Verificador:** Master Ledger (`OP_HASH_AUDIT`).
