# CORTEX-Persist: Ciclos de Madurez (Matriz 10/10)

> **"El objetivo final no es obtener una puntuación perfecta en un informe puntual, sino construir un sistema cuya calidad pueda demostrarse continuamente mediante evidencias automatizadas."**

Este documento define la trayectoria de madurez operativa y estructural de **CORTEX-Persist**, orientada a convertirlo en un proyecto comparable a infraestructuras críticas y software de alta confianza. Cada ciclo termina con evidencia objetiva, auditable y automatizada.

Para la auditoría externa y la adopción por terceros, el marco de madurez CORTEX se mapea en los siguientes **Niveles de Aseguramiento (Assurance Levels)** estandarizados:

## Assurance Levels (M0 - M6)

| Nivel | Objetivo | Estado Interno (Exergy / Legion) |
| :---: | :--- | :--- |
| **M0** | El código compila sin errores fatales. | Funcionalidad en fase fluida / Entropía alta. |
| **M1** | Integración Continua (CI) estable. | Autómatas validados contra métricas base. |
| **M2** | Baseline de deuda técnica congelada. | Cristalización de vectores. Umbral termodinámico fijado. |
| **M3** | Invariantes lógicas verificadas empíricamente. | Property Testing. El Ledger no admite mutaciones Cross-Tenant. |
| **M4** | Resistencia a fallos y apagones demostrada. | Crash Consistency y Tolerancia Bizantina (OOM, SIGKILL). |
| **M5** | Auditoría forense totalmente reproducible. | Trazabilidad Ledger determinista sin puntos ciegos. |
| **M6** | **Security Assurance Case** completo. | Operación Singularity / Singularidad Ouroboros. |

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

## CICLO 1 — Higiene (Estrategia de Cristalización Continua)
*Objetivo: Eliminar la deuda técnica al 100% de manera trazable, verificable y sin enmascaramiento (Cero `pyright: ignore` injustificados).*

La estrategia se divide en 4 fases para garantizar que el aseguramiento del código crezca estructuralmente sin bloquear el desarrollo:

### Fase 1 — Congelar la línea base
- [x] Establecer baseline actual: `78 errores` en Pyright.
- [x] Configurar CI (Quality Gates) para bloquear cualquier PR que supere los 78 errores.
*Resultado: Ningún código nuevo puede introducir deuda adicional.*

### Fase 2 — Clasificación
- [ ] Catalogar y priorizar el backlog de 78 errores (ej. P1 para `None dereference`, P2 para `Any` typing, P3 para Generics/Overloads).

### Fase 3 — Corrección por Dominio
- [ ] Semana 1: `crypto/`, `auth/`
- [ ] Semana 2: `ledger/`, `audit/`
- [ ] Semana 3: `engine/`
- [ ] Semana 4: `cli/`

### Fase 4 — Endurecimiento Progresivo del CI
- [ ] Reducir el umbral del CI de forma paulatina: `78` → `60` → `40` → `20` → `0`.
- [x] Mantener validaciones holísticas estrictas: `ruff check`, `ruff format`, `pytest`, `bandit`, y `pip-audit`.

*Resultado final: Cero errores verificables y 100% de cumplimiento en las métricas base.*

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

## CICLO 13 — Verificación formal de invariantes
*Objetivo: Comprobación automatizada de las propiedades inquebrantables del sistema.*
- [ ] Ninguna escritura entra en el ledger sin autorización.
- [ ] Todo evento tiene un identificador único.
- [ ] Toda referencia apunta a un objeto existente.
- [ ] El estado tras una recuperación es consistente.
- [ ] Una operación rechazada no deja efectos parciales.
*Resultado: Pruebas automatizadas o herramientas de verificación formal validan estos invariantes.*

---

## CICLO 14 — Pruebas de resiliencia
*Objetivo: Evaluación del comportamiento bajo condiciones adversas extremas.*
- [ ] Interrupción abrupta durante escrituras críticas.
- [ ] Reinicio inesperado del proceso principal.
- [ ] Corrupción controlada de archivos en entornos de prueba.
- [ ] Pruebas de agotamiento de recursos (CPU, RAM, descriptores de archivo).
- [ ] Fallos y latencias inyectadas en operaciones de E/S.
*Resultado: El sistema supera escenarios de estrés con comportamientos deterministas y recuperables.*

---

## CICLO 15 — Rendimiento con presupuestos
*Objetivo: Definición y cumplimiento de límites de rendimiento en el proceso de CI.*
- [ ] Tiempo de inicio ≤ presupuesto.
- [ ] Escrituras por segundo ≥ objetivo.
- [ ] Latencia p95 ≤ presupuesto.
- [ ] Consumo de memoria máximo establecido.
- [ ] Tamaño del binario compilado bajo control.
*Resultado: Cualquier regresión de rendimiento fuera de presupuesto rompe el build (CI Failure).*

---

## CICLO 16 — Compatibilidad
*Objetivo: Validación estricta en una matriz multidimensional de entornos.*
- [ ] Versiones soportadas de Python.
- [ ] Versiones de Rust y toolchains.
- [ ] Arquitecturas objetivo (x86_64, ARM64/Apple Silicon).
- [ ] Versiones de dependencias core (ej. SQLite).
*Resultado: Tests verdes en todos los nodos de la matriz antes de cada release.*

---

## CICLO 17 — Documentación verificable
*Objetivo: Documentación viva y evaluable algorítmicamente.*
- [ ] Fragmentos de código en la documentación que compilan/ejecutan en CI (Doc-tests).
- [ ] Ejemplos interactivos probados automáticamente.
- [ ] Linter de enlaces para evitar enlaces rotos o desactualizados.
- [ ] Autogeneración de diagramas a partir del código base (Mermaid, PlantUML).
*Resultado: La documentación nunca puede estar desfasada del estado del código.*

---

## CICLO 18 — Métricas de calidad
*Objetivo: Telemetría objetiva sobre la salud de la ingeniería.*
- [ ] Tiempo medio para corregir incidencias (MTTR).
- [ ] Frecuencia de despliegues (Deployment Frequency).
- [ ] Tiempo de recuperación tras fallos.
- [ ] Cobertura de pruebas (Line, Branch, Mutation).
- [ ] Edad media y criticidad de las dependencias.
*Resultado: Cuadros de mando (dashboards) que informan tendencias históricas para prevenir degradación técnica.*

---

## CICLO 19 — Gestión del riesgo
*Objetivo: Inventario estructurado y priorización causal de vulnerabilidades/defectos.*
- [ ] Modelado de amenazas registrado y actualizado.
- [ ] Evaluación de impacto y probabilidad para cada hallazgo.
- [ ] Listado de mitigaciones existentes vs riesgo residual.
- [ ] Asignación de responsabilidad y fechas límite (SLAs).
*Resultado: La deuda de seguridad se trata como operaciones matemáticas trazables y cuantificables.*

---

## CICLO 20 — Revisión periódica
*Objetivo: El sistema como entidad orgánica auditable en tiempo continuo.*
- [ ] Revisiones cíclicas de dependencias.
- [ ] Auditorías a la configuración del pipeline CI.
- [ ] Validación de cumplimiento en las políticas de firma de código.
- [ ] Simulacros de recuperación desde copias de seguridad.
*Resultado: La seguridad es una rutina asimilada en el flujo continuo, erradicando las "auditorías sorpresa".*

---

### Del "proyecto" al "sistema"
Una evolución vital es pasar de evaluar únicamente el repositorio de código a evaluar todo el ecosistema:
- Código fuente.
- Dependencias.
- Infraestructura de compilación.
- Proceso de publicación.
- Artefactos generados.
- Documentación.
- Operación y mantenimiento.

> **"Cuando cada una de esas piezas produce evidencia verificable y automatizada, la confianza en el sistema deja de depender de afirmaciones y pasa a sustentarse en pruebas reproducibles. Ese es un criterio más robusto que perseguir una puntuación '10/10' aislada, porque permite demostrar el nivel de calidad de forma continua."**

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
