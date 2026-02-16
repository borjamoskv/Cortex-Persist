# CORTEX V4.0 — Revisión Arquitectónica y de Seguridad

**Fecha:** 2026-02-16  
**Versión Auditada:** 4.0.0a1  
**Ámbito:** `cortex/api.py`, `cortex/auth.py`, `cortex/cli.py`, `cortex/engine.py` + componentes relacionados  
**Auditor:** Análisis Automatizado de Código

---

## 📋 Resumen Ejecutivo

| Categoría | Severidad | Hallazgos |
|-----------|-----------|-----------|
| **Seguridad Crítica** | 🔴 Alto | 3 vulnerabilidades |
| **Seguridad Media** | 🟡 Medio | 5 vulnerabilidades |
| **Deuda Técnica** | 🟠 Medio-Alto | 7 áreas identificadas |
| **Inconsistencias** | 🔵 Bajo | 4 inconsistencias |
| **Rendimiento** | 🟣 Medio | 3 optimizaciones pendientes |

### Estado General
✅ **Arquitectura sólida** con buena separación de responsabilidades y principios de diseño claros.  
⚠️ **Vulnerabilidades correctibles** que requieren atención antes de producción.  
⚠️ **Deuda técnica acumulada** principalmente en áreas de sincronización y manejo de errores.

---

## 🔴 Vulnerabilidades de Seguridad Críticas

### 1. CORS Configurado Permisivamente (CVSS: 5.3)
**Ubicación:** `cortex/api.py:80-86`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ← CRÍTICO: Permite cualquier origen
    allow_credentials=True,  # ← CRÍTICO: Cookies/autenticación expuestas
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impacto:** 
- Ataques CSRF desde cualquier sitio web
- Exposición de credenciales en peticiones cross-origin
- Posible acceso no autorizado a datos sensibles

**Mitigación Recomendada:**
```python
# Usar ALLOWED_ORIGINS del entorno (ya definido pero ignorado)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # ← Usar la variable definida en línea 30-33
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],  # ← Métodos explícitos
    allow_headers=["Authorization", "Content-Type"],
)
```

---

### 2. SQL Injection en Filtros Temporales (CVSS: 7.5)
**Ubicación:** `cortex/search.py:89` + `cortex/engine.py:358-366`

```python
# search.py línea 89
if temporal_filter:
    sql += f" AND f.{temporal_filter}"  # ← Concatenación directa de SQL
```

```python
# engine.py líneas 358-366
clause, params = build_temporal_filter_params(as_of)
cursor = conn.execute(
    f"""
    SELECT ... FROM facts
    WHERE project = ? AND {clause}  # ← Clause inyectado
    """,
    [project] + params,
)
```

**Impacto:**
- Ejecución arbitraria de SQL
- Exfiltración completa de base de datos
- Modificación/eliminación de datos

**PoC de Exploit:**
```python
# Un atacante podría enviar:
as_of = "2024-01-01' OR '1'='1' UNION SELECT * FROM api_keys--"
```

**Mitigación Recomendada:**
```python
# Usar solo parámetros parametrizados, nunca concatenar SQL
# El temporal_filter debería validarse contra una whitelist
ALLOWED_TEMPORAL_CLAUSES = {
    "active": "valid_until IS NULL",
    "deprecated": "valid_until IS NOT NULL"
}
```

---

### 3. Inyección de Path en Exportación (CVSS: 6.5)
**Ubicación:** `cortex/api.py:302-321`

```python
@app.get("/v1/projects/{project}/export", tags=["admin"])
async def export_project(
    project: str,
    path: Optional[str] = Query(None),  # ← Sin validación de path
    fmt: str = Query("json"),
    ...
):
    out_path = export_to_json(engine, project, path)  # ← Path inyectado
```

**Impacto:**
- Path traversal (escritura en `/etc/passwd`, etc.)
- Sobrescritura de archivos críticos del sistema

**Mitigación Recomendada:**
```python
from pathlib import Path
import re

ALLOWED_EXPORT_DIR = Path(os.environ.get("CORTEX_EXPORT_DIR", "~/.cortex/exports")).expanduser()

# Validar que el path no salga del directorio permitido
def sanitize_export_path(user_path: str) -> Path:
    # Normalizar y resolver
    target = (ALLOWED_EXPORT_DIR / user_path).resolve()
    # Verificar que está dentro del directorio permitido
    if not str(target).startswith(str(ALLOWED_EXPORT_DIR.resolve())):
        raise HTTPException(400, "Invalid path: directory traversal detected")
    return target
```

---

## 🟡 Vulnerabilidades de Seguridad Medias

### 4. Rate Limiting Stub sin Implementación
**Ubicación:** `cortex/api.py:75-78`

```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Stub for rate limiting."""
    async def dispatch(self, request: Request, call_next):
        return await call_next(request)  # ← Sin rate limiting real
```

**Impacto:**
- Vulnerable a ataques de fuerza bruta en API keys
- Posible DoS por sobrecarga de búsquedas vectoriales

**Recomendación:** Implementar rate limiting con Redis o al menos en-memoria:
```python
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis
```

---

### 5. Ausencia de Validación de Certificados SSL en Dashboard
**Ubicación:** `cortex/dashboard.py:392-395`

```javascript
const API_KEY = localStorage.getItem('cortex_key') || '';  // ← Almacenamiento en localStorage
const headers = API_KEY
  ? {'Authorization': `Bearer ${API_KEY}`, ...}
  : ...;
```

**Impacto:**
- API key almacenada en localStorage vulnerable a XSS
- Exposición a ataques de lectura de localStorage

**Recomendación:** Usar cookies `httpOnly; Secure; SameSite=Strict` con CSRF tokens.

---

### 6. Permisos Excesivos en Creación de API Keys
**Ubicación:** `cortex/api.py:467-471`

```python
raw_key, api_key = auth_manager.create_key(
    name=name,
    tenant_id=tenant_id,
    permissions=["read", "write", "admin"],  # ← Siempre admin incluido
)
```

**Impacto:**
- Cualquier usuario autenticado puede crear keys con permisos admin
- No hay granularidad de permisos en la creación

**Recomendación:** Permitir especificar permisos en la petición con validación:
```python
permissions: list[str] = Query(["read"])  # Default mínimo
# Validar contra allowed_permissions
```

---

### 7. Manejo de Errores que Expone Información Interna
**Ubicación:** `cortex/api.py:94-99`

```python
async def sqlite_error_handler(request: Request, exc: sqlite3.Error) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": f"Database error: {exc}"})
    # ↑ Expone detalles de la excepción interna
```

**Impacto:**
- Fuga de información sobre estructura de base de datos
- Potencial para ataques más dirigidos

**Recomendación:**
```python
logger.error("Database error: %s", exc)  # Log interno
return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

---

## 🟠 Deuda Técnica Significativa

### 8. Gestión Inconsistente de Conexiones SQLite
**Ubicaciones Múltiples:** `api.py`, `auth.py`, `engine.py`, `timing.py`

| Archivo | Patrón de Conexión | Problema |
|---------|-------------------|----------|
| `engine.py:103` | `check_same_thread=False` | Compartido entre hilos |
| `api.py:51` | Nueva conexión para timing | Múltiples conexiones simultáneas |
| `auth.py:92-96` | Conexión por operación | Overhead significativo |

**Problema:** SQLite no maneja bien múltiples escritores concurrentes aunque WAL ayude.

**Recomendación:** Implementar connection pooling o un patron singleton thread-safe:
```python
# cortex/db_pool.py
import queue

class ConnectionPool:
    def __init__(self, db_path: str, max_connections: int = 5):
        self._pool = queue.Queue(maxsize=max_connections)
        for _ in range(max_connections):
            self._pool.put(self._create_connection(db_path))
    
    @contextmanager
    def acquire(self):
        conn = self._pool.get()
        try:
            yield conn
        finally:
            self._pool.put(conn)
```

---

### 9. Inicialización de Componentes Globales con Estado Mutable
**Ubicación:** `cortex/api.py:37-39`, `cortex/auth.py:28`

```python
# api.py
global engine, auth_manager, tracker  # ← Variables globales mutables

# auth.py
_auth_manager: Optional[AuthManager] = None  # ← Global singleton
```

**Problemas:**
- Race conditions durante startup
- Dificulta testing unitario
- Acoplamiento implícito entre módulos

**Recomendación:** Usar inyección de dependencias de FastAPI:
```python
from fastapi import Depends

async def get_engine() -> CortexEngine:
    return app.state.engine

@app.post("/v1/facts")
async def store_fact(
    req: StoreRequest,
    engine: CortexEngine = Depends(get_engine),  # Inyectado
    auth: AuthResult = Depends(require_permission("write")),
):
    ...
```

---

### 10. Código Duplicado en Serialización JSON
**Ubicaciones:** `search.py:101-127`, `engine.py:505-529`

Mismo patrón de parsing JSON repetido 4+ veces:
```python
try:
    tags = json.loads(row[4]) if row[4] else []
except (json.JSONDecodeError, TypeError):
    tags = []
```

**Recomendación:** Crear utilidades compartidas:
```python
# cortex/utils.py
def safe_json_loads(val: Any, default: Any = None) -> Any:
    if not val:
        return default() if callable(default) else default
    try:
        parsed = json.loads(val)
        return parsed
    except (json.JSONDecodeError, TypeError):
        return default() if callable(default) else default
```

---

### 11. Hardcoding de Paths en Múltiples Lugares
**Ubicaciones:**
- `cortex/api.py:29` - `~/.cortex/cortex.db`
- `cortex/auth.py:27` - `~/.cortex/cortex.db`
- `cortex/hive.py:44` - `~/.cortex/cortex.db`
- `cortex/daemon.py:44-46` - Múltiples paths hardcodeados

**Problema:** No es configurable y dificulta testing.

---

### 12. Manejo Inconsistente de Transacciones
**Ubicación:** `cortex/engine.py:234-265`

```python
def store_many(self, facts: list[dict]) -> list[int]:
    conn = self._get_conn()
    try:
        conn.execute("BEGIN TRANSACTION")
        for f in facts:
            fid = self.store(...)  # ← Cada store hace commit interno!
        conn.commit()  # ← Commit redundante
```

**Problema:** El método `store()` ya hace `conn.commit()`, haciendo que `store_many()` no sea atómico.

**Fix:**
```python
def store_many(self, facts: list[dict]) -> list[int]:
    conn = self._get_conn()
    ids = []
    try:
        conn.execute("BEGIN EXCLUSIVE")
        for f in facts:
            fid = self._store_raw(conn, f)  # Versión sin commit
            ids.append(fid)
        conn.commit()
        return ids
    except Exception:
        conn.rollback()
        raise
```

---

### 13. Falta de Timeouts en Operaciones de Base de Datos
**Ubicaciones:** Múltiples - ninguna operación SQLite tiene timeout configurado excepto la conexión inicial.

**Riesgo:** Queries largas pueden bloquear el servidor indefinidamente.

---

## 🔵 Inconsistencias y Problemas de Diseño

### 14. Inconsistencia en Manejo de Errores HTTP
**Problema:** Mezcla de HTTPException y respuestas JSON manuales.

| Endpoint | Patrón Usado |
|----------|--------------|
| `/v1/facts` POST | `HTTPException` para auth, respuesta directa para éxito |
| `/v1/search` POST | Respuesta directa |
| `/health` | JSONResponse manual |
| `/v1/projects/{project}/export` | HTTPException para errores |

---

### 15. Contradicción en Documentación vs Implementación
**Ubicación:** `cortex/api.py:63-69`

```python
app = FastAPI(
    title="CORTEX — Sovereign Memory API",
    description="...Vector search, temporal facts, cryptographic ledger.",
    # ↑ "cryptographic ledger" pero no hay criptografía fuerte
)
```

El ledger usa SHA-256 simple (línea 493 en engine.py), no es criptográficamente verificable contra manipulación.

---

### 16. Inconsistencia en Importación de `require_auth`
**Ubicaciones:**
- `cortex/api.py:21` - `from cortex.auth import ... require_auth, require_permission`
- `cortex/hive.py:14` - `from cortex.api import require_auth`

Problema: `require_auth` se importa de `api.py` en `hive.py`, pero se define en `auth.py`. Esto crea un ciclo de importación potencial.

---

### 17. Versión Hardcodeada en Múltiples Lugares
**Ubicaciones:**
- `__init__.py:8` - `__version__ = "4.0.0a1"`
- `api.py:67,199,206,364` - `"4.0.0a1"` hardcodeado
- `schema.py:7` - `SCHEMA_VERSION = "4.0.0"`

---

## 🟣 Problemas de Rendimiento

### 18. N+1 Queries en Sincronización
**Ubicación:** `cortex/sync.py:371-398`

```python
def _get_existing_contents(...) -> set[str]:
    # Se llama una vez por tipo de fact durante sync
    rows = conn.execute(query, params).fetchall()
    return {row[0] for row in rows}
```

Se llama para `ghost`, `knowledge`, `decision`, `error`, `bridge` = múltiples queries full-scan.

**Optimización:** Cache en memoria durante la sincronización.

---

### 19. Recomputación de Embeddings sin Cache
**Ubicación:** `cortex/search.py:295-303`

```python
# Try semantic search first
try:
    embedder = self._get_embedder()
    query_embedding = embedder.embed(query)  # ← Recomputado cada vez
```

Queries repetidas computan el mismo embedding.

**Recomendación:** LRU cache para embeddings de queries frecuentes.

---

### 20. Loop O(N) Ineficiente en Daemon
**Ubicación:** `cortex/daemon.py:743-746`

```python
for _ in range(interval):
    if self._shutdown:
        break
    time.sleep(1)  # ← Check por segundo durante 5 minutos = 300 iteraciones
```

**Mejoría:** Usar `threading.Event` o `asyncio.Event` para signalización.

---

## 📊 Análisis de Dependencias

### Árbol de Importación

```
cortex/
├── __init__.py
│   └── CortexEngine (engine.py)
├── api.py
│   ├── auth.py ←─┐
│   ├── engine.py │
│   ├── timing.py │
│   ├── hive.py ←─┤
│   └── sync.py   │
├── auth.py       │
├── cli.py        │
│   └── engine.py │
├── daemon.py     │
│   └── engine.py │
├── hive.py ──────┘  # Importa require_auth de api.py (ciclo potencial)
└── ...
```

**Problema de Ciclo:** `hive.py` → `api.py` → `hive.py` (via `include_router`)

---

## ✅ Fortalezas Arquitectónicas

1. **Ledger Inmutable:** Diseño append-only con hash chaining en `engine.py:474-501`
2. **Soft Deletes:** Nunca se borran datos, solo se deprecan
3. **WAL Mode:** SQLite configurado con WAL para mejor concurrencia
4. **Input Validation:** Uso extensivo de Pydantic models en API
5. **API Key Hashing:** SHA-256 para almacenamiento seguro de keys
6. **Bootstrap Seguro:** Primera key no requiere auth, subsiguientes sí
7. **Atomicidad:** Uso de `tempfile` + `os.replace()` en write-backs

---

## 🎯 Recomendaciones Priorizadas

### Inmediato (Pre-Producción)

| Prioridad | Issue | Esfuerzo |
|-----------|-------|----------|
| P0 | Fix CORS wildcard | 30 min |
| P0 | Fix SQL injection temporal | 2 horas |
| P0 | Validar paths de export | 1 hora |
| P1 | Implementar rate limiting real | 4 horas |
| P1 | Sanitizar mensajes de error | 1 hora |

### Corto Plazo

| Prioridad | Issue | Esfuerzo |
|-----------|-------|----------|
| P2 | Connection pooling | 8 horas |
| P2 | Refactorizar store_many | 2 horas |
| P2 | Cache de embeddings | 4 horas |

### Largo Plazo

| Prioridad | Issue | Esfuerzo |
|-----------|-------|----------|
| P3 | Migrar a async SQLite | 16 horas |
| P3 | Implementar Firma de Ledger | 8 horas |
| P3 | Tests de seguridad automatizados | 16 horas |

---

## 📁 Checklist de Verificación

- [ ] CORS restringido a orígenes específicos
- [ ] SQL injection en filtros temporal parcheado
- [ ] Path traversal en exportación mitigado
- [ ] Rate limiting implementado
- [ ] Error handlers no exponen información interna
- [ ] store_many es atómicamente correcto
- [ ] Tests de seguridad añadidos (bandit, safety)
- [ ] Documentación de API actualizada
- [ ] Changelog actualizado

---

## Anexos

### A. CWEs Aplicables

| CWE | Descripción | Ubicación |
|-----|-------------|-----------|
| CWE-942 | Overly Permissive CORS | api.py:82 |
| CWE-89 | SQL Injection | search.py:89 |
| CWE-22 | Path Traversal | api.py:317 |
| CWE-209 | Info Exposure via Error Messages | api.py:96 |
| CWE-306 | Missing Auth Rate Limiting | api.py:76 |
| CWE-319 | Cleartext Storage in localStorage | dashboard.py:392 |

### B. Referencias

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/advanced/security/)
- [SQLite Concurrency](https://www.sqlite.org/wal.html)

---

**Fin del Reporte**

*Generado el 2026-02-16 | CORTEX V4.0 Security Audit*
