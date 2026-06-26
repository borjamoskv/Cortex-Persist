# CORTEX-Persist: Ciclos de Madurez (Matriz 10/10)

> **"El objetivo final no es obtener una puntuación perfecta en un informe puntual, sino construir un sistema cuya calidad pueda demostrarse continuamente mediante evidencias automatizadas."**

Este documento define la trayectoria de madurez operativa y estructural de **CORTEX-Persist**, orientada a convertirlo en un proyecto comparable a infraestructuras críticas y software de alta confianza. Cada ciclo termina con evidencia objetiva, auditable y automatizada.

---

## CICLO 0 — Base reproducible
*Objetivo: Que cualquier persona o sistema pueda reconstruir exactamente el mismo entorno.*
- [x] Builds reproducibles
- [x] `uv.lock`
- [x] `Cargo.lock`
- [x] Versionado determinista
- [x] Docker reproducible
- [x] Hashes verificables
*Resultado: "Dos máquinas distintas generan exactamente el mismo binario."*

---

## CICLO 1 — Higiene
*Objetivo: Eliminar la deuda técnica al 100%.*
- [ ] `ruff`: 0 errores
- [ ] `mypy` / `pyright`: 0 errores
- [ ] `pytest`: 100% pass
- [ ] `cargo test`: 100% pass
- [ ] `cargo clippy`: clean
- [ ] `cargo fmt`: clean
*Resultado: Cero warnings en las métricas base.*

---

## CICLO 2 — Seguridad
*Objetivo: Análisis estático de vulnerabilidades en CI/CD.*
- [ ] `cargo audit`
- [ ] `pip-audit`
- [ ] `cargo deny`
- [ ] Dependabot / Renovate
- [ ] Secret scanning
- [ ] Push protection
*Resultado: Cada PR se bloquea automáticamente si introduce fallos de seguridad conocidos.*

---

## CICLO 3 — Cadena de suministro
*Objetivo: Aseguramiento criptográfico de las dependencias.*
- [ ] SLSA Level 3+
- [ ] SBOM SPDX / CycloneDX
- [ ] Sigstore / Rekor
- [ ] Provenance
*Resultado: Responder con certeza "¿Quién compiló esto? ¿Con qué código? ¿Con qué dependencias?"*

---

## CICLO 4 — Rust (Garantías de Memoria/Propiedades)
*Objetivo: Demostrar propiedades más allá de la compilación exitosa en el núcleo Rust.*
- [ ] `cargo fuzz`
- [ ] Miri (`cargo miri`)
- [ ] Loom (concurrencia sin bloqueos)
- [ ] Kani (verificación de modelos)
- [ ] Proptest / Quickcheck
*Resultado: El núcleo no solo compila; demuestra propiedades estructurales y concurrencia segura.*

---

## CICLO 5 — SQLite (Resiliencia de Base de Datos)
*Objetivo: Garantizar la integridad ACID bajo condiciones hostiles.*
- [ ] Prevención bypass del authorizer
- [ ] Prevención write fuera de causal_write
- [ ] Control de doble commit
- [ ] Prevención de rollback parcial
- [ ] Prevención de corrupción WAL
*Resultado: Supera tests de corte eléctrico, SIGKILL y corrupción del journal.*

---

## CICLO 6 — SMT (Propiedades Lógicas)
*Objetivo: Demostrar invariantes arquitectónicos antes de aceptar cambios.*
- [ ] Nunca existe un nodo huérfano.
- [ ] Nunca aparece una dependencia circular.
- [ ] Toda firma válida implica identidad conocida.
- [ ] Toda escritura tiene causalidad.
- [ ] Toda causalidad tiene hash.
- [ ] Todo hash pertenece al ledger.
*Resultado: Verificación matemática de los invariantes C5-REAL.*

---

## CICLO 7 — Observabilidad
*Objetivo: Trazabilidad total criptográfica.*
- Responder desde el ledger: ¿Quién escribió? ¿Cuándo? ¿Por qué? ¿Qué versión? ¿Qué commit? ¿Qué firma? ¿Qué clave? ¿Qué build? ¿Qué pipeline? ¿Qué hash?
*Resultado: Todo evento es reconstruible criptográficamente.*

---

## CICLO 8 — Resiliencia
*Objetivo: Caos controlado (Chaos Engineering).*
- [ ] Matar procesos aleatorios
- [ ] Corromper SQLite
- [ ] Desconectar disco
- [ ] Llenar memoria / OOM
- [ ] Cortar red
- [ ] Reiniciar durante commits
*Resultado: El sistema recupera la invariante sin corrupción ni estado inconsistente.*

---

## CICLO 9 — Evidencia
*Objetivo: Generación de artefactos de confianza automática.*
- Carpetas autogeneradas por release:
  - `audit/`
  - `coverage/`
  - `sbom/`
  - `attestations/`
  - `benchmarks/`
  - `proofs/`
  - `performance/`
  - `security/`
*Resultado: Cero trabajo manual para generar reportes de cumplimiento.*

---

## CICLO 10 — Auditoría continua
*Objetivo: El proyecto como entidad autovalidada (Pipeline Supremo).*
- Pipeline estricto (bloqueante):
  1. Lint
  2. Tests
  3. Coverage
  4. Mutation testing
  5. Property testing
  6. Fuzzing
  7. SMT
  8. `cargo audit` / `pip-audit`
  9. SBOM
  10. Provenance
  11. Firma
  12. Release
*Resultado: Si un paso falla, `merge = bloqueado`.*

---

## CICLO 11 — Gobernanza
*Objetivo: Protocolos humanos de interacción con el repositorio.*
- [ ] Commits firmados obligatorios (GPG/SSH/Sigstore).
- [ ] Revisiones obligatorias para cambios sensibles.
- [ ] Protección de ramas (Main/Master inmutable directamente).
- [ ] Versionado Semántico estricto.
- [ ] Política de divulgación de vulnerabilidades.
- [ ] Calendario de mantenimiento documentado.

---

## CICLO 12 — Validación externa
*Objetivo: Escrutinio independiente.*
- [ ] Auditorías de seguridad por terceros.
- [ ] Programas de divulgación responsable (Bug Bounty).
- [ ] Revisión de arquitectura por expertos.
- [ ] Publicación de informes y artefactos de seguridad.

---

## Matriz de Madurez CORTEX-Persist (10/10)

| Dominio       | Criterio para 10/10                                                 |
| ------------- | ------------------------------------------------------------------- |
| Arquitectura  | Diseño documentado, pruebas de recuperación y revisión externa.     |
| Calidad       | Sin advertencias, alta cobertura y pruebas eficaces.                |
| Seguridad     | Sin vulnerabilidades críticas conocidas y controles automatizados.  |
| Supply Chain  | SBOM, procedencia SLSA, firmas y dependencias controladas.          |
| Criptografía  | Gestión robusta de claves, firmas y rotación documentada.           |
| Base de datos | Integridad verificada mediante pruebas de fallo y recuperación.     |
| Rust          | Fuzzing, pruebas de propiedades y análisis estático avanzados.      |
| Python        | Tipado, lint, pruebas y documentación mantenidos de forma continua. |
| CI/CD         | Pipelines reproducibles, protegidos y completamente automatizados.  |
| Gobernanza    | Políticas claras, revisiones y auditorías periódicas.               |
