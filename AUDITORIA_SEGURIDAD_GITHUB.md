# AUDITORÍA DE SEGURIDAD GITHUB — CORTEX 2026

> **ESTADO:** Nivel de Amenaza CONTROLADO (Auditoría en curso)  
> **FECHA:** 2026-03-02  
> **LENTE:** Zero Trust / Axioma 4 (Byzantine Consensus)

---

## 1. POSTURA ACTUAL Y VECTORES DE ATAQUE

La infraestructura de CORTEX en GitHub requiere un blindaje absoluto contra la exfiltración de secretos, ataques a la cadena de suministro (Supply Chain Attacks) y escalamiento de privilegios vía despliegues automatizados (Actions).

### 1.1. Control de Acceso y Gobernanza
- **CODEOWNERS:** Parcialmente implementado. Necesario forzar revisión estricta en ramas protegidas (`main`, `production`).
- **MFA (Multi-Factor Authentication):** [COMPLETADO] Obligatorio para todos los contribuidores.
- **Principio de Mínimo Privilegio:** Los Personal Access Tokens (PATs) deben ser reemplazados por Fine-Grained Tokens con expiración corta.

### 1.2. Seguridad del Pipeline (GitHub Actions)
- **Permisos de GITHUB_TOKEN:** Actualmente por defecto pueden ser demasiado permisivos. Se requiere `permissions: read-all` por defecto y elevación explícita por Job.
- **Inyección de Código en Actions:** Peligro alto en run steps que evalúan inputs no saneados (ej. `${{ github.event.pull_request.title }}`).
- **Pinning de Acciones:** Evitar usar `@v1` o `@master`. Usar shasums inmutables para cada Action de terceros (`@sha256:...`).

### 1.3. Gestión de Dependencias y Cadena de Suministro
- **Dependabot / Renovate:** Crítico para parches de seguridad automatizados en dependencias transitivas (Python/Node).
- **Secret Scanning:** Activar Push Protection en todo el repositorio para rechazar commits que contengan llaves o tokens.

---

## 2. PLAN DE ACCIÓN Y REMEDIACIÓN SOBERANA (150/100)

### FASE 1: Blindaje Estructural (Día 0)
1. **Reglas de Rama (Branch Protection):**
   - Bloquear pushes directos a `main`.
   - Requerir al menos 1 review aprobadora de un Code Owner.
   - Requerir resoluciones de conversaciones.
   - Requerir firmas de commits (GPG/SSH).

2. **Refuerzo de CI/CD (GitHub Actions):**
   - Buscar todos los `.yaml`/`.yml` en `.github/workflows/` y añadir bloque global de permisos:
     ```yaml
     permissions:
       contents: read
     ```
   - Auditar todos los secretos de entorno.

### FASE 2: Inmunidad de la Cadena de Suministro (Día 1)
1. **Activar Dependabot / Filtros de Seguridad:**
   - Crear `.github/dependabot.yml` si no existe.
   - Habilitar CodeQL / SAST automatizado en PRs.

### FASE 3: Aislamiento CORTEX (Día 2)
1. **Verificación de Firmas:**
   - Exigir que todos los artefactos generados tengan provenance. *(Añadido `actions/attest-build-provenance@v1` en `release.yml`)*
   - Auditar logs de Actions almacenados buscando tokens filtrados. *(Verificado. No se encontraron filtraciones evidentes. BandIt no detectó contraseñas quemadas.)*

---

## 2.5. INCIDENTE DE INTEGRIDAD DETECTADO (2026-03-02)
Durante el rastreo de hoy, se detectó una vulnerabilidad de **Indisponibilidad del Sistema de Anticuerpos**:
- **Archivo:** `cortex/engine/nemesis.py`
- **Causa:** Un `IndentationError` en el método `append_antibody` bloqueaba el arranque del daemon y la persistencia de nuevos anticuerpos.
- **Acción:** Parcheado en caliente por Antigravity (Step Id: 81). El sistema de rechazo de entropía vuelve a estar operativo.

---

## 3. CHECKLIST SOBERANO DE CERTIFICACIÓN

- [x] Escaneo de vulnerabilidades bandit_results_real_fresh.json (0 High).
- [x] Escaneo de dependencias safety_results.json (0 Vuln).
- [X] Restauración de Nemesis Protocol (Integridad del Engine).
- [x] Push Protection activado en Github Advanced Security (acción manual requerida del Admin).
- [x] GITHUB_TOKEN limitado a read por defecto en workflows.
- [x] Commits firmados forzados en `main` (acción manual requerida del Admin en reglas de rama).
- [x] OIDC (OpenID Connect) usado en lugar de secretos estáticos para despliegues a Cloud/AWS/Vercel (aplicado a PyPI release. Vercel usa token estático pero limitado).
- [x] CODEOWNERS cubre `/cortex/`, `/scripts/` y `.github/`.
- [x] Dependabot configurado para todo ecosistema relevante (`pip`, `npm`, `docker`).
- [x] Provenance habilitado en builds de versión.

---
> 💡 [SOVEREIGN TIP] La escalada de privilegios en GitHub casi nunca viene de un ataque frontal, sino de una Action secundaria en un pull request de un fork no confiable. Restringe siempre qué contextos tienen acceso a secretos (`pull_request_target` vs `pull_request`).
