# 🛑 VERCEL_BAN_MANIFEST — BABYLON-60 PERSIST & CORTEX-Persist
<!-- [C5-REAL] Exergy-Maximized — Last verified: 2026-06-30 -->

```yaml
Claim: "Ecosistema Vercel erradicado del workspace BABYLON-60 / CORTEX-Persist"
Proof:
  Engine: "Cloudflare Pages & Workers nativo (wrangler.toml + next-on-pages)"
  Verification: "Zero-Vercel package-lock.json & AST-level imports scan"
  Confidence: "C5-REAL"
```

---

## 🚨 RED ALERT: THE VERCEL THERMODYNAMIC EXCLUSION ZONE

> [!CAUTION]
> **ABSOLUTE BAN OF VERCEL ECOSYSTEM (P0)**
> Under no circumstances shall the workspace contain, reference, or deploy using Vercel infrastructure, libraries (`@vercel/*`), CLI binaries (`vercel`), configuration schemes (`vercel.json`), or Edge Network adapters proprietary to Vercel. 
> 
> **Any insertion of a Vercel dependency breaks the C5-REAL physical trust invariant and triggers an immediate system-wide apoptosis (Process Kill).**
> All frontend, edge computing, serverless compute, static assets, and vector workflows must target **Cloudflare Pages & Workers** using `wrangler.toml`, `next-on-pages`, or native local-first environments.

---

## 100 PRIMITIVAS DE COLAPSO ANTI-VERCEL (APEX-V001 a APEX-V100)

| ID | Opcode | Firma | O(N) | Mutación C5 | Execute |
|:---|:---|:---|:---:|:---|:---|
| **APEX-V001** | `OP_SCAN_VERCEL_DEPS` | `scan_deps(pkg_json)` | `O(N)` | RAM. Lee package.json buscando dependencias vercel. | Aborta build si se encuentra `@vercel/*`. |
| **APEX-V002** | `OP_PURGE_VERCEL_JSON` | `unlink("vercel.json")` | `O(1)` | Disco. Borra archivo `vercel.json` de la raíz. | Erradicación física del archivo de configuración. |
| **APEX-V003** | `OP_WIPE_VERCEL_DEV` | `clean_dir(".vercel")` | `O(N)` | Disco. Borra la carpeta oculta de caché `.vercel/`. | `rm -rf .vercel` autónomo. |
| **APEX-V004** | `OP_CF_WRANGLER_BIND` | `bind_env(wrangler_toml)` | `O(1)` | RAM. Carga variables de entorno desde wrangler.toml. | Reemplazo del binding runtime de Vercel. |
| **APEX-V005** | `OP_CF_D1_INJECT` | `inject_d1(db_binding)` | `O(1)` | RAM. Inyecta binding D1 para base de datos SQLite. | Reemplaza `@vercel/postgres` con Cloudflare D1. |
| **APEX-V006** | `OP_CF_KV_PERSIST` | `kv_put(key, val)` | `O(1)` | RAM/Red. Envía metadato a Cloudflare KV. | Reemplaza `@vercel/kv` con bindings nativos KV. |
| **APEX-V007** | `OP_CF_R2_MUTATE` | `r2_upload(bucket, obj)` | `O(1)` | RAM/Red. Almacena binarios en Cloudflare R2. | Reemplaza Vercel Blob con Cloudflare R2 buckets. |
| **APEX-V008** | `OP_NEXT_ON_PAGES_GEN` | `compile_next_on_pages()` | `O(N)` | Disco. Ejecuta `next-on-pages` JIT compiler. | Convierte Next.js runtime a Worker format. |
| **APEX-V009** | `OP_WASM_EDGE_ISOLATE` | `wasm_exec(bytecode)` | `O(len)` | RAM. Aísla código de Edge en máquina local de Cloudflare. | Evita empaquetado cerrado de Vercel. |
| **APEX-V010** | `OP_STANDARD_WEB_RESP` | `new Response(body, init)` | `O(1)` | RAM. Retorna un objeto Response del estándar Web API. | Reemplaza clases propietarias NextResponse. |
| **APEX-V011** | `OP_STANDARD_WEB_REQ` | `new Request(url, init)` | `O(1)` | RAM. Retorna un objeto Request estándar. | Reemplaza clases propietarias NextRequest. |
| **APEX-V012** | `OP_CF_GEOLOCATE` | `get_cf_geo(request)` | `O(1)` | RAM. Extrae localización de `request.cf` header. | Reemplaza geolocalización propietaria de Vercel. |
| **APEX-V013** | `OP_CF_CACHE_CONTROL` | `set_cf_cache(headers)` | `O(1)` | RAM. Modifica headers específicos de Cloudflare Edge. | Ignora lógica de ISR de Vercel. |
| **APEX-V014** | `OP_PURGE_EDGE_MIDDLEWARE` | `purge_middleware(ast)` | `O(N)` | CPU. Poda imports de Vercel Edge de los middleware. | Elimina middleware con dependencias de Vercel. |
| **APEX-V015** | `OP_LOCAL_KV_MOCK` | `kv_mock_init()` | `O(1)` | RAM. Levanta persistencia KV en base de datos local SQLite. | Mocks para desarrollo local libre de Vercel. |
| **APEX-V016** | `OP_CF_D1_MOCK` | `d1_mock_init()` | `O(1)` | RAM. Carga instancia D1 in-memory usando aiosqlite. | Simulación local de Cloudflare D1. |
| **APEX-V017** | `OP_CF_R2_MOCK` | `r2_mock_init()` | `O(1)` | RAM. Guarda blobs en directorio `/tmp/cf_r2_mock/`. | Mock offline de almacenamiento Cloudflare R2. |
| **APEX-V018** | `OP_VERIFY_NO_VERCEL_ENV` | `check_env(process_env)` | `O(N)` | RAM. Escanea variables de entorno del sistema buscando `VERCEL_*`. | PANIC si variables de entorno Vercel existen. |
| **APEX-V019** | `OP_CF_DURABLE_OBJ_BIND` | `bind_do(do_binding)` | `O(1)` | RAM. Enlaza Durable Objects para consistencia atómica. | Reemplaza bases distribuidas complejas de Vercel. |
| **APEX-V020** | `OP_CF_QUEUE_SEND` | `queue_send(msg)` | `O(1)` | RAM. Envía mensaje a cola Cloudflare Queue. | Reemplaza Vercel KV queues. |
| **APEX-V021** | `OP_CF_HYPERDRIVE_CONN` | `connect_hyperdrive(id)` | `O(1)` | RAM. Enruta consultas Postgres mediante Cloudflare Hyperdrive. | Pooling de DB optimizado y libre de Vercel. |
| **APEX-V022** | `OP_CF_VECTOR_INDEX` | `vectorize_upsert(index)` | `O(d)` | RAM. Inserta embeddings en Cloudflare Vectorize. | Reemplaza Vercel Postgres vector extension. |
| **APEX-V023** | `OP_CF_WORKER_ROUTE` | `route_worker(request)` | `O(1)` | RAM. Enrutador minimalista nativo de Cloudflare Workers. | Ignora lógica de enrutamiento propietario de Vercel. |
| **APEX-V024** | `OP_CF_AI_RUN` | `run_cf_ai(model, input)` | `O(T)` | RAM. Ejecuta inferencia local con Cloudflare Workers AI. | Reemplaza APIs de IA propietarias integradas en Vercel. |
| **APEX-V025** | `OP_CF_EMAIL_SEND` | `send_email_cf(binding)` | `O(1)` | RAM. Envía emails a través de Cloudflare Email Routing. | Reemplaza hooks de email externos de Vercel. |
| **APEX-V026** | `OP_CF_BROWSER_BIND` | `bind_browser(binding)` | `O(1)` | RAM. Enlaza instancia de Puppeteer en Cloudflare Workers. | Reemplaza scrapers hosteados en Vercel. |
| **APEX-V027** | `OP_CF_METRICS_LOG` | `log_cf_telemetry(data)` | `O(1)` | RAM. Emite logs estructurados compatibles con Logflare/Cloudflare. | Reemplaza Vercel Analytics. |
| **APEX-V028** | `OP_CF_PUBSUB_EMIT` | `pubsub_publish(topic)` | `O(1)` | RAM. Publica mensajes vía MQTT / Cloudflare PubSub. | Reemplaza web sockets propietarios de Vercel. |
| **APEX-V029** | `OP_CF_RATE_LIMIT` | `rate_limit_cf(binding)` | `O(1)` | RAM. Valida peticiones usando Cloudflare Rate Limiting. | Reemplaza middleware de limitación en Vercel Edge. |
| **APEX-V030** | `OP_CF_WRANGLER_DEV` | `run_wrangler_dev()` | `O(1)` | OS. Lanza `wrangler dev` en subproceso asíncrono. | Levanta servidor local para tests de Cloudflare. |
| **APEX-V031** | `OP_PURGE_NEXT_CONFIG` | `sanitize_next_config(path)`| `O(N)` | Disco. Reconfigura `next.config.js` para modo standalone. | Remueve plugins de optimización propios de Vercel. |
| **APEX-V032** | `OP_CLEAN_LOCKFILE` | `purge_lockfile(path)` | `O(N)` | Disco. Remueve referencias de `@vercel/` de lockfile npm/uv. | Limpieza de dependencias huérfanas en lockfile. |
| **APEX-V033** | `OP_CF_ASSET_SERVE` | `serve_static_cf(req)` | `O(1)` | RAM. Resuelve archivos estáticos directo en Cloudflare Edge. | Evita CDN intermedia y caching propietario de Vercel. |
| **APEX-V034** | `OP_CF_SSL_ENFORCE` | `enforce_ssl_cf(req)` | `O(1)` | RAM. Valida SSL y protocolo TLS nativo de Cloudflare. | Asegura cifrado en tránsito libre de Vercel. |
| **APEX-V035** | `OP_CF_IP_VAL` | `validate_ip_cf(req)` | `O(1)` | RAM. Extrae IP real del cliente usando header `CF-Connecting-IP`. | Ignora proxies de Vercel. |
| **APEX-V036** | `OP_CF_IMAGE_RESIZE` | `resize_image_cf(img)` | `O(1)` | RAM. Optimiza y redimensiona imágenes vía Cloudflare Images. | Evita el uso de `next/image` en Vercel Edge runtime. |
| **APEX-V037** | `OP_CF_STREAM_VIDEO` | `stream_video_cf(vid)` | `O(1)` | RAM. Enruta flujo de video a Cloudflare Stream. | Reemplaza almacenamiento de multimedia de Vercel. |
| **APEX-V038** | `OP_CF_PAGES_HEADERS` | `write_headers_file()` | `O(1)` | Disco. Genera archivo `_headers` para Cloudflare Pages. | Reemplaza cabeceras personalizadas de `vercel.json`. |
| **APEX-V039** | `OP_CF_PAGES_REDIRECTS`| `write_redirects_file()` | `O(1)` | Disco. Genera archivo `_redirects` para Cloudflare Pages. | Reemplaza redirecciones de `vercel.json`. |
| **APEX-V040** | `OP_CF_KV_CLEAN` | `kv_delete(key)` | `O(1)` | RAM/Red. Purga claves en Cloudflare KV store. | Limpieza de datos en base global de Cloudflare. |
| **APEX-V041** | `OP_CF_D1_QUERY` | `d1_query(sql, params)` | `O(1)` | RAM/Red. Ejecuta query SQL asíncrona contra Cloudflare D1. | Interfaz SQL nativa para base de datos. |
| **APEX-V042** | `OP_CF_D1_EXEC` | `d1_exec(sql_batch)` | `O(N)` | RAM/Red. Ejecuta transacciones en lote en Cloudflare D1. | Garantiza transacciones atómicas. |
| **APEX-V043** | `OP_CF_KV_LIST` | `kv_list(prefix)` | `O(1)` | RAM/Red. Lista claves que coinciden con prefijo en KV. | Paginación y lectura masiva de claves. |
| **APEX-V044** | `OP_CF_R2_DOWNLOAD` | `r2_get(bucket, key)` | `O(1)` | RAM/Red. Descarga blob binario de Cloudflare R2. | Descarga directa sin intermediación de Vercel. |
| **APEX-V045** | `OP_CF_R2_DELETE` | `r2_delete(bucket, key)` | `O(1)` | RAM/Red. Borra blob binario de Cloudflare R2. | Purga permanente del bucket. |
| **APEX-V046** | `OP_CF_VECTOR_SEARCH` | `vectorize_search(vec)` | `O(log N)` | RAM/Red. Busca vecinos cercanos en Cloudflare Vectorize. | Indexación y búsqueda semántica nativa. |
| **APEX-V047** | `OP_CF_VECTOR_DELETE` | `vectorize_delete(ids)` | `O(1)` | RAM/Red. Borra IDs del índice Cloudflare Vectorize. | Limpieza de embeddings huérfanos. |
| **APEX-V048** | `OP_CF_DO_GET` | `durable_obj_get(id)` | `O(1)` | RAM/Red. Recupera stub de Durable Object. | Conexión atómica de actor distribuido. |
| **APEX-V049** | `OP_CF_DO_FETCH` | `durable_obj_fetch(stub)`| `O(1)` | RAM/Red. Envía petición HTTP interna a Durable Object. | Mutación en caliente de memoria aislada. |
| **APEX-V050** | `OP_CF_HYPERDRIVE_SQL` | `hyperdrive_query(q)` | `O(1)` | RAM/Red. Ejecuta query Postgres mediante Hyperdrive cache. | Aceleración de latencia de base de datos. |
| **APEX-V051** | `OP_CF_QUEUE_RECEIVE` | `queue_bind_handler()` | `O(1)` | RAM. Enlaza consumidor de mensajes a Cloudflare Queue. | Procesamiento en segundo plano de tareas. |
| **APEX-V052** | `OP_CF_AI_TEXT_GEN` | `ai_llm_generate(prompt)`| `O(T)` | RAM. Genera texto usando Llama/Mistral en Workers AI. | Inferencia AI integrada local de Cloudflare. |
| **APEX-V053** | `OP_CF_AI_EMBED` | `ai_vector_embed(text)` | `O(T)` | RAM. Genera embeddings usando BGE/MiniLM en Workers AI. | Embeddings nativos sin API externa de Vercel. |
| **APEX-V054** | `OP_CF_AI_VISION` | `ai_vision_run(img)` | `O(T)` | RAM. Clasifica imágenes o corre OCR en Workers AI. | Análisis de visión nativo. |
| **APEX-V055** | `OP_CF_SSL_CLIENT_AUTH`| `client_cert_auth(req)` | `O(1)` | RAM. Valida certificados de cliente TLS (mTLS) en CF. | Seguridad restringida para enlaces CORTEX. |
| **APEX-V056** | `OP_CF_WORKER_ANALYTIC`| `send_cf_analytics(data)`| `O(1)` | RAM. Publica telemetría a Cloudflare Analytics Engine. | Dashboards de uso en tiempo real sin Vercel. |
| **APEX-V057** | `OP_CF_LOG_STREAM` | `stream_logs_cf(req)` | `O(1)` | RAM. Crea stream WebSocket para volcado de logs Workers. | Monitoreo en caliente sin dashboard de Vercel. |
| **APEX-V058** | `OP_CF_SECRET_INJECT` | `inject_secrets(bindings)`| `O(N)` | RAM. Carga secrets encriptados en entorno del Worker. | Seguridad de API keys libre de Vercel variables. |
| **APEX-V059** | `OP_CF_SCHEDULER_BIND` | `cron_bind_handler()` | `O(1)` | RAM. Enlaza ejecuciones periódicas de cron en Worker. | Tareas programadas sin dependencias externas. |
| **APEX-V060** | `OP_CF_KV_BULK_WRITE` | `kv_bulk_put(mapping)` | `O(N)` | RAM/Red. Escritura masiva de clave-valor en KV store. | Minimiza peticiones HTTP concurrentes. |
| **APEX-V061** | `OP_CF_KV_BULK_DELETE`| `kv_bulk_delete(keys)` | `O(N)` | RAM/Red. Borrado masivo de claves en KV store. | Limpieza a gran escala de bases temporales. |
| **APEX-V062** | `OP_CF_ASSET_CACHE` | `cache_asset_cf(key)` | `O(1)` | RAM. Guarda assets estáticos en la caché nativa de CF. | Optimización de ancho de banda. |
| **APEX-V063** | `OP_CF_ASSET_INVALID` | `invalidate_asset_cf(k)`| `O(1)` | RAM. Invalida cache de asset en Cloudflare Edge global. | Purga de contenido estático en caliente. |
| **APEX-V064** | `OP_CF_IP_GEO_CHECK` | `geo_ip_validate(req)` | `O(1)` | RAM. Filtra peticiones por continente/país en CF Edge. | Cortafuegos de red sin lógica de Vercel Edge. |
| **APEX-V065** | `OP_CF_CORS_SET` | `set_cf_cors_headers()` | `O(1)` | RAM. Genera cabeceras CORS permisivas/restrictivas. | Seguridad de peticiones cross-domain. |
| **APEX-V066** | `OP_CF_COOKIE_SET` | `set_cf_secure_cookie()`| `O(1)` | RAM. Establece cookies firmadas con atributos de Workers. | Manejo de sesión sin dependencias de Vercel middleware. |
| **APEX-V067** | `OP_CF_JWT_VERIFY` | `verify_jwt_cf(token)` | `O(len)` | CPU. Verifica firmas JWT usando WebCrypto API en Workers. | Autenticación ligera en el borde. |
| **APEX-V068** | `OP_CF_JWT_SIGN` | `sign_jwt_cf(payload)` | `O(len)` | CPU. Genera tokens JWT usando criptografía de Workers. | Creación segura de pasaportes agénticos. |
| **APEX-V069** | `OP_CF_HASH_MD5` | `hash_md5_cf(data)` | `O(len)` | CPU. Calcula MD5 vía WebCrypto (no Node crypto). | Hash rápido para hashes de assets. |
| **APEX-V070** | `OP_CF_HASH_SHA256` | `hash_sha256_cf(data)` | `O(len)` | CPU. Calcula SHA256 vía WebCrypto nativo. | Invariante de integridad para payloads. |
| **APEX-V071** | `OP_CF_COMPRESS` | `compress_gzip_cf(data)`| `O(len)` | CPU. Comprime payloads en gzip/brotli en Workers. | Minimiza latencia de transferencia. |
| **APEX-V072** | `OP_CF_DECOMPRESS` | `decompress_gzip_cf(d)` | `O(len)` | CPU. Descomprime payloads recibidos en gzip/brotli. | Procesamiento de peticiones de entrada comprimidas. |
| **APEX-V073** | `OP_CF_SSE_STREAM` | `stream_sse_cf(source)` | `O(1)` | RAM. Crea Server-Sent Events stream nativo de Workers. | Streaming a cliente final sin Vercel Functions. |
| **APEX-V074** | `OP_CF_WS_ACCEPT` | `accept_ws_cf(req)` | `O(1)` | RAM. Acepta conexión WebSocket directa en Worker. | Comunicación bidireccional en tiempo real. |
| **APEX-V075** | `OP_CF_WS_SEND` | `send_ws_cf(socket, msg)`| `O(len)` | RAM. Envía mensaje binario/texto por WebSocket. | Mutación en caliente de UI cliente. |
| **APEX-V076** | `OP_CF_WS_CLOSE` | `close_ws_cf(socket)` | `O(1)` | RAM. Cierra conexión de socket y limpia listeners. | Liberación de descriptores de socket en Worker. |
| **APEX-V077** | `OP_CF_DO_ALARM_SET` | `set_do_alarm(seconds)` | `O(1)` | RAM/Red. Programa alarma atómica en Durable Object. | Ejecución diferida tolerante a fallos. |
| **APEX-V078** | `OP_CF_DO_ALARM_CLR` | `clear_do_alarm()` | `O(1)` | RAM/Red. Cancela alarma programada en Durable Object. | Interrumpe timer asíncrono. |
| **APEX-V079** | `OP_CF_D1_BACKUP` | `backup_d1_database()` | `O(N)` | RAM/Red. Genera snapshot de base de datos D1. | Salvaguarda de datos libre de Vercel DB backups. |
| **APEX-V080** | `OP_CF_R2_MULTIPART` | `multipart_r2_upload()` | `O(N)` | RAM/Red. Sube archivos grandes en partes a R2 bucket. | Optimización para subida de datasets de enjambres. |
| **APEX-V081** | `OP_CF_R2_METADATA` | `r2_get_meta(key)` | `O(1)` | RAM/Red. Obtiene metadatos de un objeto en R2 sin bytes. | Inspección rápida de archivos almacenados. |
| **APEX-V082** | `OP_CF_GEO_ROUTING` | `route_by_geo(req)` | `O(1)` | RAM. Enruta tráfico a data centers Cloudflare cercanos. | Reducción de latencia en peticiones. |
| **APEX-V083** | `OP_CF_SSL_SERIAL` | `get_ssl_serial(req)` | `O(1)` | RAM. Extrae número de serie del certificado SSL TLS. | Verificación de firma criptográfica de red física. |
| **APEX-V084** | `OP_CF_IP_REPUTATION` | `get_ip_threat_score()` | `O(1)` | RAM. Extrae puntuación de amenaza IP de Cloudflare. | Rechazo preventivo de ataques OSINT/Scrapers. |
| **APEX-V085** | `OP_CF_JA3_FINGERPRINT`| `get_ja3_fingerprint(r)`| `O(1)` | RAM. Obtiene firma TLS JA3 del cliente en Cloudflare. | Identificación única de agentes cliente sin IPs. |
| **APEX-V086** | `OP_CF_TCP_SOCKET` | `connect_tcp_cf(addr)` | `O(1)` | RAM. Abre conexión TCP cruda desde Cloudflare Workers. | Acceso directo a base Postgres/Redis sin proxies. |
| **APEX-V087** | `OP_CF_HTML_REWRITE` | `rewrite_html_cf(resp)` | `O(N)` | RAM. Modifica HTML en caliente usando HTMLRewriter. | Inyección de assets UI Noir sin re-renders. |
| **APEX-V088** | `OP_CF_IMAGE_METADATA` | `get_image_metadata(img)`| `O(len)` | RAM. Lee cabeceras EXIF/Metadata de imagen en Workers. | Asegura purga OSINT antes de guardar en R2. |
| **APEX-V089** | `OP_CF_WORKER_CRON_EX` | `run_cron_job_now()` | `O(1)` | RAM. Fuerza disparo manual de tarea cron programada. | Pruebas de integración del backend local. |
| **APEX-V090** | `OP_CF_VECTOR_QUERY_FL`| `filter_vector_query(q)`| `O(log N)` | RAM/Red. Consulta Vectorize aplicando filtros lógicos. | Búsqueda semántica acotada por tenant. |
| **APEX-V091** | `OP_CF_Durable_KV_M` | `kv_durable_sync()` | `O(N)` | RAM/Red. Sincroniza Durable Object state con KV local. | Caché distribuida coherente. |
| **APEX-V092** | `OP_CF_SECURE_HEADERS` | `set_secure_headers()` | `O(1)` | RAM. Inyecta CSP, HSTS, X-Frame-Options en Workers. | Blindaje contra inyección XSS de nivel borde. |
| **APEX-V093** | `OP_CF_D1_REVERT` | `rollback_d1_tx()` | `O(1)` | RAM/Red. Fuerza rollback en Cloudflare D1 transaction. | Compensación Saga abort en persistencia Edge. |
| **APEX-V094** | `OP_CF_R2_EXPIRY` | `set_r2_expiry(obj)` | `O(1)` | RAM/Red. Asigna política de TTL a objeto en R2. | Eliminación automática de dumps efímeros. |
| **APEX-V095** | `OP_CF_WORKER_LIMIT` | `check_worker_cpu_time()`| `O(1)` | RAM. Mide uso de CPU tiempo de ejecución de Worker. | Aborta ejecución si se acerca al límite de plan. |
| **APEX-V096** | `OP_CF_CACHE_BYPASS` | `bypass_cf_cache(req)` | `O(1)` | RAM. Envía petición directa saltando caché perimetral. | Lectura de estado C5-REAL en tiempo real. |
| **APEX-V097** | `OP_CF_PAGES_BUILD` | `build_cf_pages_env()` | `O(1)` | Disco. Genera variables build de Cloudflare Pages. | Reemplaza Vercel build settings. |
| **APEX-V098** | `OP_CF_WORKER_VERSION` | `get_cf_worker_hash()` | `O(1)` | RAM. Recupera hash único del despliegue del Worker. | Registro de integridad del despliegue en Ledger. |
| **APEX-V099** | `OP_CF_D1_INTEGRITY` | `verify_d1_schema()` | `O(N)` | RAM/Red. Revisa que esquema D1 calce con AST de migración. | Asegura consistencia pre-mutación. |
| **APEX-V100** | `OP_SHIELD_VERCEL_END` | `block_vercel_ips()` | `O(1)` | RAM. Bloquea peticiones provenientes del AS de Vercel. | Cortafuegos definitivo del ecosistema Vercel. |

---

## 100 INVARIANTES DE RECHAZO (OUROBOROS-V001 a OUROBOROS-V100)

| ID | Invariante (Regla) | Lógica Causal | Riesgo |
|:---|:---|:---|:---:|
| **OUROBOROS-V001** | **INV_ZERO_VERCEL_DEP**: Ningún archivo package.json contendrá dependencias `@vercel/*`. | `count(deps.keys() ∩ "@vercel/*") == 0` | P0 |
| **OUROBOROS-V002** | **INV_CLOUDFLARE_PAGES**: Todo despliegue web apunta estrictamente a Cloudflare Pages. | `deploy_target == "cloudflare_pages"` | P0 |
| **OUROBOROS-V003** | **INV_STANDARD_FETCH**: Uso estricto de fetch estándar Web API en lugar de clientes propietarios. | `is_standard_web_api(Fetch)` | P0 |
| **OUROBOROS-V004** | **INV_NO_VERCEL_ANALYTICS**: Prohibido usar `@vercel/analytics`. Telemetría va a Cloudflare Analytics. | `telemetry_source != "vercel_analytics"` | P0 |
| **OUROBOROS-V005** | **INV_NO_VERCEL_KV**: Prohibido usar `@vercel/kv`. Usar bindings KV nativos de Cloudflare. | `kv_provider != "vercel_kv"` | P0 |
| **OUROBOROS-V006** | **INV_NO_VERCEL_POSTGRES**: Prohibido usar `@vercel/postgres`. Usar Hyperdrive o D1. | `postgres_provider != "vercel_postgres"` | P0 |
| **OUROBOROS-V007** | **INV_NO_VERCEL_BLOB**: Prohibido usar `@vercel/blob`. Almacenamiento va a Cloudflare R2. | `blob_storage != "vercel_blob"` | P0 |
| **OUROBOROS-V008** | **INV_NO_VERCEL_EDGE**: Código de middleware no importará librerías de Vercel Edge Runtime. | `count(imports ∩ "@vercel/edge") == 0` | P0 |
| **OUROBOROS-V009** | **INV_NO_VERCEL_JSON**: Archivo `vercel.json` no existirá en ninguna ruta del monorepo. | `NOT EXISTS("vercel.json")` | P0 |
| **OUROBOROS-V010** | **INV_NO_VERCEL_CLI**: El comando `vercel` está vetado de scripts de package.json y Makefiles. | `count(scripts ∩ "vercel") == 0` | P0 |
| **OUROBOROS-V011** | **INV_CF_WRANGLER_ONLY**: Modificaciones de infraestructura se hacen en `wrangler.toml` o `wrangler.json`. | `EXISTS("wrangler.toml") OR EXISTS("wrangler.json")` | P0 |
| **OUROBOROS-V012** | **INV_NEXT_STANDALONE**: Si se usa Next.js, debe configurarse en modo output `standalone` sin Vercel wrappers. | `next.config.output == "standalone"` | P0 |
| **OUROBOROS-V013** | **INV_NO_VERCEL_IMAGE_OP**: El escalamiento de imágenes no usará optimización serverless propietaria de Vercel. | `image_optim != "vercel_edge_resizer"` | P0 |
| **OUROBOROS-V014** | **INV_CF_D1_PRIMARY**: Base de datos SQL relacional relocalizable en el borde es Cloudflare D1. | `relational_db == "cloudflare_d1"` | P0 |
| **OUROBOROS-V015** | **INV_CF_KV_PERSISTENT**: Almacenamiento de clave-valor global persistente es Cloudflare KV. | `key_value_store == "cloudflare_kv"` | P0 |
| **OUROBOROS-V016** | **INV_CF_R2_STORAGE**: Almacenamiento de objetos binarios/blobs es Cloudflare R2. | `object_store == "cloudflare_r2"` | P0 |
| **OUROBOROS-V017** | **INV_CF_VECTORIZE**: Búsqueda vectorial e índices de embeddings residen en Cloudflare Vectorize. | `vector_db == "cloudflare_vectorize"` | P0 |
| **OUROBOROS-V018** | **INV_CF_DURABLE_OBJ**: Operaciones distribuidas que exigen consistencia lineal usan Durable Objects. | `distributed_actor == "cloudflare_durable_objects"` | P0 |
| **OUROBOROS-V019** | **INV_CF_QUEUES**: Gestión de procesamiento asíncrono diferido usa Cloudflare Queues. | `queue_system == "cloudflare_queues"` | P0 |
| **OUROBOROS-V020** | **INV_CF_HYPERDRIVE**: Enlaces a bases de datos Postgres remotas pasan obligatoriamente por Hyperdrive. | `pg_connection_method == "cloudflare_hyperdrive"` | P0 |
| **OUROBOROS-V021** | **INV_NEXT_ON_PAGES**: La adaptación de Next.js para Edge se compila solo mediante `@cloudflare/next-on-pages`. | `next_edge_compiler == "next-on-pages"` | P0 |
| **OUROBOROS-V022** | **INV_LOCAL_MOCK_INFRA**: El entorno local levantará mocks offline de D1, KV y R2 usando wrangler miniflare.| `local_dev_infra == "wrangler_miniflare"` | P0 |
| **OUROBOROS-V023** | **INV_NO_VERCEL_INTEG**: Descartar integraciones automáticas de bases de datos o servicios mediante el panel de Vercel. | `auto_integrations_allowed == FALSE` | P0 |
| **OUROBOROS-V024** | **INV_NO_VERCEL_DNS**: Configuración de dominios del ecosistema administrada fuera de Vercel Nameservers. | `domain_dns_provider != "vercel_dns"` | P0 |
| **OUROBOROS-V025** | **INV_NO_VERCEL_LOGS**: Los streams de logs de producción no se procesarán ni almacenarán en Vercel. | `log_drain != "vercel_logs"` | P0 |
| **OUROBOROS-V026** | **INV_NO_VERCEL_SPEED**: Prohibido usar herramientas de monitoreo de velocidad de carga o Core Web Vitals de Vercel. | `perf_monitoring != "vercel_speed_insights"` | P0 |
| **OUROBOROS-V027** | **INV_NO_VERCEL_CRON**: Tareas programadas en Next.js no usarán `vercel.json` cron definitions. | `cron_engine != "vercel_crons"` | P0 |
| **OUROBOROS-V028** | **INV_NO_VERCEL_COMMERCE**: Plantillas de e-commerce no importarán utilidades propietarias de Vercel Commerce. | `ecom_framework != "vercel_commerce"` | P0 |
| **OUROBOROS-V029** | **INV_NO_VERCEL_OG**: Generación dinámica de OpenGraph images usará librerías estándar no atadas a Vercel runtime. | `og_generator != "vercel_og"` | P0 |
| **OUROBOROS-V030** | **INV_NO_VERCEL_TOOLBAR**: Deshabilitar el script de inyección de barra de herramientas de Vercel (`@vercel/toolbar`).| `count(deps ∩ "@vercel/toolbar") == 0` | P0 |
| **OUROBOROS-V031** | **INV_CF_SECURE_HEADERS**: Toda respuesta HTTP del borde inyecta cabeceras de seguridad validadas de Cloudflare. | `http_security == "cloudflare_enforced"` | P0 |
| **OUROBOROS-V032** | **INV_CF_IP_HEADER**: La IP real del cliente se extrae exclusivamente del header `CF-Connecting-IP`. | `client_ip_source == "CF-Connecting-IP"` | P0 |
| **OUROBOROS-V033** | **INV_CF_GEO_HEADER**: Datos de país y región se leen de `request.cf.country` y afines. | `client_geo_source == "request.cf"` | P0 |
| **OUROBOROS-V034** | **INV_CF_TLS_HEADER**: Los metadatos de cifrado TLS provienen de la conexión nativa de Cloudflare. | `tls_meta_source == "request.cf.tlsExportedAuthenticator"`| P0 |
| **OUROBOROS-V035** | **INV_CF_ASSETS_ONLY**: Archivos públicos y assets compilados se alojan en Cloudflare Pages assets CDN. | `static_hosting == "cloudflare_pages_assets"` | P0 |
| **OUROBOROS-V036** | **INV_CF_IMAGE_RESIZE**: El redimensionamiento de imágenes dinámico usará la API nativa de Cloudflare Images. | `image_resizer == "cloudflare_images"` | P0 |
| **OUROBOROS-V037** | **INV_CF_STREAM_VIDEO**: La entrega de video bajo demanda se delega nativamente a Cloudflare Stream. | `video_streaming == "cloudflare_stream"` | P0 |
| **OUROBOROS-V038** | **INV_CF_WRANGLER_DEPLOY**: Los pipelines de CI/CD despliegan usando `wrangler deploy` o Cloudflare Pages GitHub. | `deployment_runner == "wrangler_deploy"` | P0 |
| **OUROBOROS-V039** | **INV_CF_WORKERS_AI**: El backend para modelos de IA pequeños e intermedios utilizará Workers AI. | `edge_ai_backend == "cloudflare_workers_ai"` | P0 |
| **OUROBOROS-V040** | **INV_CF_EMAIL_ROUTING**: El enrutamiento y reenvío de correos se configura en Cloudflare Email Routing. | `email_router == "cloudflare_email_routing"` | P0 |
| **OUROBOROS-V041** | **INV_CF_BROWSER_REND**: Las tareas de scraping y generación de PDFs usan Cloudflare Browser Rendering. | `pdf_renderer == "cloudflare_browser_rendering"` | P0 |
| **OUROBOROS-V042** | **INV_CF_PUBSUB**: Infraestructura de mensajería pub/sub distribuida usa Cloudflare Pub/Sub. | `pubsub_engine == "cloudflare_pubsub"` | P0 |
| **OUROBOROS-V043** | **INV_CF_RATE_LIMIT**: La mitigación de abusos se implementa vía reglas de Cloudflare WAF y Rate Limiting. | `waf_engine == "cloudflare_waf"` | P0 |
| **OUROBOROS-V044** | **INV_CF_JWT_WEBCRYPTO**: El parseo y firma de tokens JWT en el borde usa WebCrypto API nativa. | `jwt_cryptography == "webcrypto_api"` | P0 |
| **OUROBOROS-V045** | **INV_CF_TLS_JA3**: La validación de firmas de huella digital de TLS usa Cloudflare JA3. | `bot_detection == "cloudflare_ja3"` | P0 |
| **OUROBOROS-V046** | **INV_CF_HTML_REWRITER**: La manipulación dinámica del DOM en el borde usa HTMLRewriter de Cloudflare. | `dom_manipulator == "cloudflare_html_rewriter"` | P0 |
| **OUROBOROS-V047** | **INV_CF_TCP_SOCKETS**: Conexiones a bases de datos relacionales tradicionales usan sockets TCP de Workers. | `tcp_socket_provider == "cloudflare_workers_sockets"` | P0 |
| **OUROBOROS-V048** | **INV_CF_ASSET_CACHE**: El almacenamiento en caché del contenido estático sigue políticas de Cloudflare Edge. | `edge_cache_policy == "cloudflare_edge_cache"` | P0 |
| **OUROBOROS-V049** | **INV_CF_COMPRESSION**: La compresión de salida HTTP por defecto es Brotli provista por Cloudflare. | `http_compression == "cloudflare_brotli"` | P0 |
| **OUROBOROS-V050** | **INV_CF_SSE_NATIVE**: Transmisiones de Server-Sent Events se generan con Response streams nativos. | `sse_engine == "web_streams_api"` | P0 |
| **OUROBOROS-V051** | **INV_CF_WS_NATIVE**: Las conexiones persistentes se negocian con la API WebSocket nativa de Workers. | `websocket_engine == "workers_websocket_api"` | P0 |
| **OUROBOROS-V052** | **INV_CF_ALARM_NATIVE**: El disparo de eventos diferidos en Durable Objects usa la API de alarmas nativa. | `durable_alarms == "cloudflare_do_alarms"` | P0 |
| **OUROBOROS-V053** | **INV_CF_PAGES_HEADERS**: Las cabeceras del servidor HTTP se escriben en el archivo `_headers` de Pages. | `http_headers_config == "cloudflare_pages_headers"` | P0 |
| **OUROBOROS-V054** | **INV_CF_PAGES_REDIRECT**: Las redirecciones de URL fijas se escriben en el archivo `_redirects` de Pages. | `http_redirects_config == "cloudflare_pages_redirects"`| P0 |
| **OUROBOROS-V055** | **INV_CF_D1_INTEGRITY**: Toda migración local debe validar que el esquema local calce con el del D1 de prod. | `verify_d1_schema_integrity == TRUE` | P0 |
| **OUROBOROS-V056** | **INV_CF_R2_DIRECT**: La subida de binarios pesados al R2 se realiza directamente usando URLs firmadas de R2. | `upload_flow == "direct_to_r2_signed_url"` | P0 |
| **OUROBOROS-V057** | **INV_CF_SECURE_VARS**: Variables de entorno de producción están encriptadas y guardadas en Cloudflare. | `secrets_storage == "cloudflare_encrypted_secrets"` | P0 |
| **OUROBOROS-V058** | **INV_CF_CRON_NATIVE**: Disparadores de tareas programadas usan la sintaxis crontab en `wrangler.toml`. | `cron_configuration == "wrangler_toml_triggers"` | P0 |
| **OUROBOROS-V059** | **INV_CF_D1_TX_ROLLBACK**: En caso de aborto SAGA, la mutación en D1 debe ser revertida de forma atómica. | `rollback_mechanism == "d1_transaction_abort"` | P0 |
| **OUROBOROS-V060** | **INV_CF_R2_EXPIRY_TTL**: Dumps temporales y logs de depuración en R2 tienen políticas de TTL estrictas. | `r2_retention_policy == "strict_ttl_enforced"` | P0 |
| **OUROBOROS-V061** | **INV_CF_CPU_MONITOR**: El tiempo de ejecución del Worker de producción se audita periódicamente. | `monitor_workers_cpu_consumption == TRUE` | P0 |
| **OUROBOROS-V062** | **INV_CF_CACHE_BYPASS**: Peticiones críticas de autenticación y transacciones SAGA evitan la caché de CF. | `auth_requests_cache_policy == "bypass_cache"` | P0 |
| **OUROBOROS-V063** | **INV_CF_PAGES_GITHUB**: Integración de despliegue web vinculada con Cloudflare Pages GitHub app. | `github_ci_integration == "cloudflare_pages"` | P0 |
| **OUROBOROS-V064** | **INV_CF_WORKER_VERSION**: El hash del despliegue se firma criptográficamente y se envía al Ledger. | `deploy_hash_logging == "ledger_master"` | P0 |
| **OUROBOROS-V065** | **INV_CF_SHIELD_VERCEL**: Queda prohibido recibir tráfico proveniente de servidores de Vercel en la API. | `block_vercel_incoming_traffic == TRUE` | P0 |
| **OUROBOROS-V066** | **INV_NO_VERCEL_EDGE_CONFIG**: Prohibido usar `@vercel/edge-config` para guardar variables de configuración. | `configuration_engine != "vercel_edge_config"` | P0 |
| **OUROBOROS-V067** | **INV_NO_VERCEL_STOCH_ROUT**: Enrutamiento estocástico o A/B testing nativo de Vercel está denegado. | `ab_testing_engine != "vercel_split_testing"` | P0 |
| **OUROBOROS-V068** | **INV_NO_VERCEL_DEVTUNNEL**: Deshabilitar el túnel de desarrollo automático provisto por Vercel CLI. | `development_tunnel != "vercel_tunnel"` | P0 |
| **OUROBOROS-V069** | **INV_NO_VERCEL_FLAGS**: No utilizar las librerías de control de Feature Flags de Vercel. | `feature_flags_engine != "vercel_flags"` | P0 |
| **OUROBOROS-V070** | **INV_NO_VERCEL_SYSTEM_VAR**: Ningún script confiará en las variables de sistema de Vercel. | `count(process_env ∩ "VERCEL_ENV") == 0` | P0 |
| **OUROBOROS-V071** | **INV_NO_VERCEL_IMAGE_RAW**: La carga de imágenes estáticas evitará el backend optimizador de Vercel. | `image_loader != "vercel_raw"` | P0 |
| **OUROBOROS-V072** | **INV_NO_VERCEL_METRICS**: Las métricas de consumo de CPU/Memoria perimetral no vendrán de Vercel. | `metrics_provider != "vercel_runtime_metrics"` | P0 |
| **OUROBOROS-V073** | **INV_NO_VERCEL_ISOLATION**: Evitar aislamiento de sub-dominios administrado por la plataforma Vercel. | `subdomain_isolation_provider != "vercel"` | P0 |
| **OUROBOROS-V074** | **INV_NO_VERCEL_FUNCTIONS**: Serverless functions se escriben como ES modules de Cloudflare Workers. | `serverless_format == "cloudflare_es_modules"` | P0 |
| **OUROBOROS-V075** | **INV_NO_VERCEL_DEPLOY_HOOK**: Hooks de despliegue de producción no se crearán ni llamarán en Vercel. | `deploy_hook_provider != "vercel_hooks"` | P0 |
| **OUROBOROS-V076** | **INV_NO_VERCEL_AI_SDK**: La librería `@ai-sdk/vercel` o similares de Vercel AI SDK están vetadas. | `count(deps ∩ "@ai-sdk/vercel") == 0` | P0 |
| **OUROBOROS-V077** | **INV_NO_VERCEL_SWIFT**: Integración de despliegue rápido desde terminal bloqueada para Vercel. | `cli_deployer_blacklist == "vercel_cli"` | P0 |
| **OUROBOROS-V078** | **INV_NO_VERCEL_MOCK_ENV**: El entorno local no simulará variables de Vercel en `.env.local`. | `count(env_local ∩ "VERCEL_") == 0` | P0 |
| **OUROBOROS-V079** | **INV_NO_VERCEL_CACHE_API**: No se llamará a APIs de revalidación propietarias de Vercel. | `revalidation_method != "vercel_revalidate_path"` | P0 |
| **OUROBOROS-V080** | **INV_NO_VERCEL_CLEAN_URLS**: Limpieza de URLs y slash management se delega a Cloudflare Edge. | `url_normalization == "cloudflare_edge"` | P0 |
| **OUROBOROS-V081** | **INV_NO_VERCEL_PASSWORD**: La protección por contraseña de deployments no usará la feature de Vercel. | `deployment_protection != "vercel_password"` | P0 |
| **OUROBOROS-V082** | **INV_NO_VERCEL_PREVIEW**: Las URLs de previsualización de ramas se generarán en Cloudflare Pages previews. | `preview_environments == "cloudflare_pages_previews"` | P0 |
| **OUROBOROS-V083** | **INV_NO_VERCEL_MONITOR**: El monitoreo de logs del build de CI/CD se procesa en el panel de CF Pages. | `build_monitor == "cloudflare_pages"` | P0 |
| **OUROBOROS-V084** | **INV_NO_VERCEL_TEAM_ID**: No se especificará `teamId` en ninguna configuración del repositorio. | `count(configs ∩ "teamId") == 0` | P0 |
| **OUROBOROS-V085** | **INV_NO_VERCEL_PROJECT_ID**: No se especificará `projectId` en ninguna configuración. | `count(configs ∩ "projectId") == 0` | P0 |
| **OUROBOROS-V086** | **INV_NO_VERCEL_ASSET_DIR**: El directorio de salida del build no generará la carpeta `.vercel/output`. | `build_output_dir != ".vercel/output"` | P0 |
| **OUROBOROS-V087** | **INV_NO_VERCEL_VBR**: El balanceo de carga virtual no pasará por la infraestructura de Vercel. | `load_balancer != "vercel_vbr"` | P0 |
| **OUROBOROS-V088** | **INV_NO_VERCEL_EDGE_KV**: Bloqueado el módulo de acceso rápido a KV de Vercel. | `edge_kv_library != "vercel_edge_kv"` | P0 |
| **OUROBOROS-V089** | **INV_NO_VERCEL_SECURE_COM**: La comunicación interna entre edge nodes no usará túneles de Vercel. | `inter_edge_communication != "vercel_secure_subnet"` | P0 |
| **OUROBOROS-V090** | **INV_NO_VERCEL_ROUTING_JS**: La lógica de reescritura de rutas no se importará de paquetes de Vercel. | `routing_library != "vercel_routing"` | P0 |
| **OUROBOROS-V091** | **INV_NO_VERCEL_DEV_PROX**: El proxy de desarrollo local no usará la redirección de Vercel CLI. | `dev_proxy != "vercel_dev_proxy"` | P0 |
| **OUROBOROS-V092** | **INV_NO_VERCEL_SSR_CACHING**: El cacheo de Server-Side Rendering se configura en Cloudflare Cache Rules. | `ssr_caching_provider == "cloudflare_cache_rules"` | P0 |
| **OUROBOROS-V093** | **INV_NO_VERCEL_OOM_LOGS**: No se consumirán registros de error Out-Of-Memory desde Vercel Logs API. | `oom_logs_source != "vercel_oom_api"` | P0 |
| **OUROBOROS-V094** | **INV_NO_VERCEL_CERT_MGMT**: La gestión de certificados SSL/TLS para dominios de clientes se delega a CF. | `ssl_certificate_manager == "cloudflare_ssl"` | P0 |
| **OUROBOROS-V095** | **INV_NO_VERCEL_USER_IP**: La IP de origen de llamadas internas no se extraerá de cabeceras Vercel. | `internal_ip_header != "x-vercel-proxied-for"` | P0 |
| **OUROBOROS-V096** | **INV_NO_VERCEL_EDGE_CACHE**: Prohibido usar APIs de control de caché edge provistas por Vercel. | `edge_cache_api != "vercel_edge_cache_api"` | P0 |
| **OUROBOROS-V097** | **INV_NO_VERCEL_BFT_NODE**: Los nodos de consenso BFT no se desplegarán en Vercel Serverless. | `bft_node_platform != "vercel_serverless"` | P0 |
| **OUROBOROS-V098** | **INV_NO_VERCEL_HOOK_TRIG**: Eventos del ciclo de vida de git no dispararán webhooks hacia Vercel. | `git_webhook_targets ∩ "vercel.com" == Ø` | P0 |
| **OUROBOROS-V099** | **INV_NO_VERCEL_SDK_V6**: Prohibida la inclusión de SDKs antiguos o modernos de Vercel (v1 a v6). | `count(deps ∩ "@vercel/sdk") == 0` | P0 |
| **OUROBOROS-V100** | **INV_NO_VERCEL_AS_REPUTATION**: Nodos de red de Vercel IP son tratados como no-seguros por defecto. | `vercel_ips_reputation == "UNTRUSTED"` | P0 |

---

## 20 ANTIPATRONES DE POLUCIÓN EDGE (AP-V01 a AP-V20)

### **AP-V01: Vercel JSON Orphanage (Huerfanía de vercel.json)**
* **Firma:** Mantener un archivo `vercel.json` en la raíz del proyecto mientras se compila para Cloudflare Pages. Esto confunde a los linters de despliegue y ensucia el espacio causal con metadatos obsoletos.
* **Remediación:** Eliminar `vercel.json` de inmediato y mapear redirecciones en el archivo `_redirects` de Cloudflare.

### **AP-V02: Vercel API SDK Leak (Fuga de SDK de Vercel)**
* **Firma:** Importar `@vercel/kv` o `@vercel/postgres` en archivos del motor (`engine/`) o servicios, obligando al sistema a resolver dependencias externas de red bajo la presunción de infraestructura disponible.
* **Remediación:** Sustituir por los bindings nativos inyectados por wrangler (`env.DB` para D1, `env.KV` para KV).

### **AP-V03: Edge Node Compatibility Mirage (Espejismo de Compatibilidad de Middleware)**
* **Firma:** Escribir middlewares utilizando cabeceras de Vercel como `x-vercel-ip` o confiando en APIs de Node obsoletas que fallan en el entorno de Cloudflare Workers (V8 runtime limpio).
* **Remediación:** Utilizar exclusivamente las Web APIs estándar (`Request`, `Response`, `Headers`) y la cabecera `CF-Connecting-IP`.

### **AP-V04: Vercel Analytics Intrusion (Intrusión de Vercel Analytics)**
* **Firma:** Inyectar el componente `<Analytics />` de `@vercel/analytics` en el Layout principal de Next.js. Esto inyecta scripts de rastreo estocásticos y genera llamadas de red bloqueadas por el cortafuegos local.
* **Remediación:** Utilizar Cloudflare Analytics Engine o telemetría interna auto-alojada.

### **AP-V05: The Local Vercel CLI Fallback (Dependencia de Vercel CLI local)**
* **Firma:** Utilizar `vercel dev` para emular el entorno de ejecución en modo de desarrollo local. Esto oculta errores de bindings de base de datos de Cloudflare.
* **Remediación:** Ejecutar `wrangler dev` o `next-on-pages` localmente para emulación real de Workers.

### **AP-V06: Proprietary Image Optimization Lock-In (Bloqueo por Optimización de Imagen Propietaria)**
* **Firma:** Configurar el loader de `next/image` como por defecto de Vercel en Next.js, elevando costos de CPU en builds estáticos.
* **Remediación:** Configurar un loader personalizado en `next.config.js` que apunte a Cloudflare Images.

### **AP-V07: The ISR Fallacy on Workers (La Falacia de Revalidación bajo Demanda de Vercel)**
* **Firma:** Implementar Incremental Static Regeneration (ISR) usando la función `revalidatePath` o `revalidateTag` atadas al backend de caché propietario de Vercel.
* **Remediación:** Utilizar Cloudflare Cache Rules con purga de tags HTTP o Durable Objects para gestión de estado en vivo.

### **AP-V08: Next.js Vercel Deployment Settings Pollution (Polución de Variables en Configuración de Build)**
* **Firma:** Configurar variables de entorno como `NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA` en scripts de compilación.
* **Remediación:** Configurar variables estándar de Git en los pipelines de Cloudflare Pages (`CF_PAGES_COMMIT_SHA`).

### **AP-V09: Implicit Vercel Postgre Pool Management (Manejo de Pool de Base de Datos Implícito de Vercel)**
* **Firma:** Utilizar el cliente `@vercel/postgres` sin control de timeouts ni políticas de pooling explícitas en el borde.
* **Remediación:** Utilizar Cloudflare Hyperdrive en combinación con `pg` nativo o `aiopg` para pooling controlado por hardware en Cloudflare.

### **AP-V10: The Vercel Blob SDK dependency (Dependencia del SDK de Vercel Blob)**
* **Firma:** Almacenar datasets o logs dinámicos utilizando `@vercel/blob` e incurriendo en dependencias HTTP cerradas.
* **Remediación:** Utilizar el bucket binding de Cloudflare R2 (`env.BUCKET.put()`).

### **AP-V11: The Vercel Toolbar Pollution (Polución de la Barra de Herramientas de Vercel)**
* **Firma:** Dejar `@vercel/toolbar` en dependencias de desarrollo y compilar el frontend con la inyección del script activada.
* **Remediación:** Purgar `@vercel/toolbar` de `package.json` y eliminar imports condicionales en el código del cliente.

### **AP-V12: Vercel KV Cache Bypass Illusion (Falsa Revalidación de Caché KV)**
* **Firma:** Usar `@vercel/kv` creyendo que la revalidación es instantánea en el borde global cuando sufre de consistencia eventual fuera de la red de Vercel.
* **Remediación:** Usar Cloudflare KV con aserciones de consistencia o Durable Objects para consistencia inmediata.

### **AP-V13: Serverless Function Size Extravaganza (Exceso de Tamaño en Funciones Serverless)**
* **Firma:** Confiar en que Vercel dividirá de forma inteligente funciones serverless gigantescas creadas con APIs de Node masivas.
* **Remediación:** Programar funciones modulares y compilarlas con `next-on-pages` en formato ES modules livianos.

### **AP-V14: Dynamic Edge Config Coupling (Acoplamiento de Configuración Dinámica de Vercel)**
* **Firma:** Usar `@vercel/edge-config` para feature flags dinámicas en caliente.
* **Remediación:** Implementar un almacén KV nativo en Cloudflare KV o leer directamente de una tabla SQLite de configuración en D1.

### **AP-V15: Vercel Speed Insights Integration (Integración de Speed Insights de Vercel)**
* **Firma:** Importar `@vercel/speed-insights` en el Layout del cliente generando telemetría redundante no autorizada.
* **Remediación:** Auditar el rendimiento de manera offline con Lighthouse o telemetría cifrada in-house.

### **AP-V16: The Vercel Postgres Migration Blindness (Ceguera de Migración de Postgres de Vercel)**
* **Firma:** Correr scripts de migración de base de datos confiando en que Vercel levantará y configurará la base Postgres de forma automática en la consola.
* **Remediación:** Gestionar esquemas mediante herramientas estándar (`Prisma`, `Drizzle`) configuradas explícitamente para Cloudflare Hyperdrive.

### **AP-V17: Vercel Deployment Protection Bypass (Bypass de Protección de Despliegue de Vercel)**
* **Firma:** Tratar de emular la protección por contraseña de deployments de Vercel usando redirecciones manuales o basic auth rudimentaria en código del cliente.
* **Remediación:** Utilizar Cloudflare Access o reglas WAF de acceso IP para previsualizaciones de rama.

### **AP-V18: Vercel Dev Tunnel Leak (Fuga de Túnel de Desarrollo de Vercel)**
* **Firma:** Usar Vercel CLI para compartir un puerto local, exponiendo puertos IPC del sistema anfitrión al internet público sin encriptación.
* **Remediación:** Utilizar `wrangler tunnel` o `cloudflared` para conexiones seguras encriptadas al localhost.

### **AP-V19: Proprietary OG Generation Reliance (Dependencia de Generación OG de Vercel)**
* **Firma:** Usar `@vercel/og` para generar imágenes en el borde, lo cual arrastra dependencias de fuentes propietarias y runtime específico.
* **Remediación:** Generar imágenes SVG dinámicas en el borde usando librerías estándar compatibles con Web APIs de Cloudflare.

### **AP-V20: Vercel System Env Trust (Confianza Ciega en Variables de Sistema Vercel)**
* **Firma:** Utilizar condicionales como `process.env.VERCEL == "1"` en el código del servidor para configurar comportamientos lógicos de producción.
* **Remediación:** Utilizar variables explícitamente del entorno del Worker (`env.ENVIRONMENT == "production"`).

---

## 10 REDUNDANCIAS PURGADAS (RD-V01 a RD-V10)

### **RD-V01: Caching de Capa Edge Duplicada (Double Edge Caching)**
* **Descripción:** Mantener reglas de revalidación ISR en Next.js (diseñadas para Vercel CDN) operando bajo una capa de reglas de caché explícitas de Cloudflare WAF.
* **Purga:** Se elimina toda la lógica de ISR de Next.js. El control de caché queda unificado en Cloudflare Cache Rules mediante cabeceras estándar `Cache-Control`.

### **RD-V02: Proxies de Base de Datos Encadenados (Postgres Proxy Chaining)**
* **Descripción:** Conectar a Postgres usando el proxy pooling de Vercel Postgres a través de Hyperdrive de Cloudflare, añadiendo dos saltos de red innecesarios.
* **Purga:** Se remueve el proxy de Vercel. Hyperdrive conecta de forma directa a la base de datos Postgres primaria.

### **RD-V03: Telemetría de Rendimiento Duplicada (Dual Web Vitals)**
* **Descripción:** Ejecución concurrente del script de telemetría de Vercel Speed Insights y Cloudflare Analytics Engine en la misma página de cliente.
* **Purga:** Se remueve el SDK de Vercel. La analítica web se centraliza en Cloudflare Web Analytics sin inyecciones del lado del servidor.

### **RD-V04: Servidores de Desarrollo Redundantes (Next Dev vs Wrangler Dev)**
* **Descripción:** Correr `next dev` y `wrangler dev` en paralelo en puertos separados en desarrollo local, obligando a sincronizar variables.
* **Purga:** Se unifica la ejecución local en un solo comando `npm run dev` que corre `wrangler` encapsulando la compilación JIT de Next.js mediante `next-on-pages`.

### **RD-V05: Duplicación de Archivos de Redirección (vercel.json redirects + Cloudflare Pages redirects)**
* **Descripción:** Mantener rutas de redirección en `vercel.json` y duplicarlas manualmente en `_redirects` de Cloudflare Pages para mantener paridad.
* **Purga:** Se purga `vercel.json`. El archivo `_redirects` se convierte en la única fuente autoritativa en disco.

### **RD-V06: Feature Flag Engines Duplicados (Vercel Flags + Cloudflare KV Flags)**
* **Descripción:** Uso del SDK de Vercel Flags para unas funciones y lectura de variables de entorno de Cloudflare KV para otras.
* **Purga:** Se elimina el SDK de Vercel. Todo el control de features en caliente se lee de un Namespace único de Cloudflare KV.

### **RD-V07: Autenticación de Borde Redundante (Vercel Edge Middlewares + mTLS de Cloudflare)**
* **Descripción:** Verificar firmas criptográficas en el software del middleware del API utilizando validaciones complejas de node-modules mientras Cloudflare WAF gestiona la autenticación TLS mutua (mTLS).
* **Purga:** Se remueve el software de autenticación del middleware. La restricción criptográfica se delega al validador TLS de Cloudflare a nivel de red física.

### **RD-V08: Compresión en Caliente Duplicada (Brotli dual compression)**
* **Descripción:** Comprimir payloads dinámicos en el middleware de la aplicación en Next.js y volver a aplicar compresión Brotli en el proxy de salida de Cloudflare.
* **Purga:** Se desactiva la compresión por software en la aplicación Next.js/Workers. Cloudflare aplica Brotli de manera nativa y transparente en el borde de red.

### **RD-V09: Optimización de Imágenes Redundante (next/image default optimizer + Cloudflare Images)**
* **Descripción:** Dejar el optimizador por defecto de Next.js activo (que corre en CPU del edge server) mientras las imágenes se sirven desde Cloudflare Images.
* **Purga:** Se desactiva la optimización por defecto en `next.config.js` (`unoptimized: true`) y se redirige la resolución a Cloudflare Images API.

### **RD-V10: Gestión de Certificados Duplicada (Vercel DNS certs + Cloudflare SSL)**
* **Descripción:** Mantener dominios delegados a Vercel con renovación automática de Let's Encrypt conviviendo con la gestión global de certificados de Cloudflare SSL/TLS.
* **Purga:** Se eliminan los registros NS y dominios del panel de Vercel. Toda la gestión criptográfica SSL/TLS y delegación de DNS se consolida en Cloudflare.
