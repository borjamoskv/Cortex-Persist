# SDK Packaging Map — CORTEX Persist

> Auditoría de los 3 puntos de packaging del monorepo. Fecha: 2026-03-20.

## Tres pyproject.toml — scope distinto, sin colisión de funcionalidad

| Directorio | Package name | Versión | Scope | Build backend |
|:-----------|:-------------|:--------|:------|:--------------|
| `/` (raíz) | `cortex-persist` | `0.3.0b2` | **Engine completo** — ledger, memory, guards, CLI, API, daemon | setuptools |
| `cortex-sdk/` | `cortex-persist-client` ✅ | `0.1.0` | **Cliente HTTP** — thin wrapper sobre la REST API | setuptools legacy |
| `sdks/python/` | `cortex-persist-sdk` | `0.1.0` | **Cliente HTTP** — zero dependencies, hatchling | hatchling |

## Colisión de nombre — RESUELTA ✅

`cortex-sdk/pyproject.toml` fue renombrado de `cortex-persist` → `cortex-persist-client`.
La colisión con el engine está eliminada. Árbol de publicación PyPI limpio:


```
cortex-sdk/ → DEPRECATED (no publicar)
sdks/python/ → CANONICAL SDK externo (publicar como cortex-persist-sdk)
/            → CANONICAL engine (publicar como cortex-persist)
```

### URLs de repositorio inconsistentes

| Fichero | `Repository` URL |
|:--------|:----------------|
| `/pyproject.toml` | `https://github.com/borjamoskv/cortex` ← incorrecto |
| `cortex-sdk/pyproject.toml` | `https://github.com/borjamoskv/cortex-persist` ← correcto |
| `sdks/python/pyproject.toml` | `https://github.com/borjamoskv/cortex` ← incorrecto |

**Acción:** Actualizar `[project.urls]` en `/pyproject.toml` y `sdks/python/pyproject.toml`
al slug correcto: `https://github.com/borjamoskv/Cortex-Persist`.

## Estado de dependencias

| Paquete | Dependencias runtime |
|:--------|:--------------------|
| `cortex-persist` (engine) | 15 deps — sentence-transformers, sqlite-vec, cryptography, keyring, pydantic, aiosqlite... |
| `cortex-persist-sdk` (sdks/python) | **0 deps** — stdlib only |
| `cortex-persist` (cortex-sdk) | `httpx>=0.25` — 1 dep |

El SDK en `sdks/python/` es el más limpio para distribución externa. Candidato natural para publicación.
