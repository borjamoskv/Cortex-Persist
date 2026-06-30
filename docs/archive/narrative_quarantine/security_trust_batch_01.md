# ONTOLOGY-FORGE-OMEGA: SECURITY & CRYPTOGRAPHIC TRUST (BATCH 1)
**Dominio:** Seguridad, Criptografía, Gestión de Llaves e Inmutabilidad C5-REAL
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL

## MATRIZ 1: 20 PRIMITIVAS DE COLAPSO (SEC-P01..20)
Mecanismos elementales de fallo de seguridad y brecha criptográfica en el sistema.

| ID | Primitiva | Mecanismo Causal | Activación (Trigger) | Sensor (Síntoma) | Escala Temporal | Gravedad | Intervención |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **SEC-P01** | `OP_KEY_EXPOSURE` | Fuga de llave privada en logs o trazas de error. | Variable de entorno o stack trace escrita a disco. | Expresión regular detecta llave en `/logs/`. | O(1) | P0 | Apoptosis instantánea y rotación de llaves. |
| **SEC-P02** | `OP_SIGN_BYPASS` | Validación criptográfica de firmas falsamente positiva. | Error de lógica condicional en middleware. | Mutación sin registro de firma en DB. | MS | P0 | Bloqueo estricto del write-path. |
| **SEC-P03** | `OP_MERKE_COLLISION` | Dos payloads distintos producen el mismo hash de bloque. | Colisión accidental o inducida en árbol Merkle. | `HashMismatch` en verificación de procedencia. | O(N) | P0 | Aborto de transacción y recreación del árbol. |
| **SEC-P04** | `OP_REPLAY_ATTACK` | Reinyección de payload encriptado válido para duplicar acción. | Falta de nonce único o salt temporal expirado. | `DuplicateKeyError` en transacciones del Ledger. | <10ms | P1 | Taint binding con timestamp UTC obligatorio. |
| **SEC-P05** | `OP_DECRYPT_FAIL` | Pérdida de acceso a llaves para descifrar datos persistidos. | Corrupción de almacén de claves (OS Keyring). | `DecryptionError` en lectura del fact store. | Lenta | P0 | Re-inicialización de base de datos desde copia. |
| **SEC-P06** | `OP_ENTROPY_DEPLETE` | Generador de números aleatorios produce claves predecibles. | Falta de entropía en el sistema (/dev/urandom). | Claves repetidas o patrones en generación. | Continua | P0 | Bloqueo de generación de claves en el runtime. |
| **SEC-P07** | `OP_KEYRING_DISCONNECT`| Pérdida de conexión con el llavero del sistema operativo (OS Keyring). | Servicio de seguridad bloqueado por el anfitrión. | `KeyringLockedException` en inicialización. | MS | P1 | Transición a almacenamiento de claves en memoria aislada. |
| **SEC-P08** | `OP_PLAINTEXT_LEAK` | Almacenamiento de datos sensibles sin cifrar en disco. | Error en parser de serialización JSON. | Datos confidenciales legibles en sqlite. | O(N) | P0 | Purga de tablas y re-cifrado mediante AES-GCM. |
| **SEC-P09** | `OP_REVOKED_KEY_USE` | Uso de clave comprometida y revocada para firmar. | Falta de actualización del registro de revocaciones. | Firma válida de ID revocada en la transacción. | Segundos | P0 | Invalidación del bloque y aislamiento del nodo emisor. |
| **SEC-P10** | `OP_TAINT_FORGERY` | Falsificación de firma CORTEX-TAINT de procedencia. | Acceso no autorizado al generador de firmas. | Discordancia entre hash y payload en el validador. | O(1) | P0 | Cierre de socket y apoptosis de worker. |
| **SEC-P11** | `OP_SIDE_CHANNEL_LEAK`| Fuga de información por análisis de tiempo de ejecución de firmas. | Comparación de strings no constante en validación. | Variabilidad predecible en el tiempo de respuesta. | MS | P2 | Reemplazar por `constant_time_compare` en verificación. |
| **SEC-P12** | `OP_CIPHER_DOWNGRADE` | Negociación forzada de algoritmos de cifrado débiles. | Configuración incorrecta en cliente HTTP. | Conexión SSL/TLS establecida en Cipher débil. | Segundos | P1 | Rechazo de conexión y forzado de TLS 1.3 estricto. |
| **SEC-P13** | `OP_RNG_DRIFT` | Desviación del generador de entropía física por hardware. | Fallo físico en sensor TPM/Secure Enclave. | Distribución no uniforme en muestras de test de aleatoriedad. | Continua | P0 | Derivación a generador de respaldo por software. |
| **SEC-P14** | `OP_UNVERIFIED_BINARY`| Ejecución de binario compilado sin verificación de firma digital. | script.py corre comando sin validar SHA-256 local. | Proceso ejecutado fuera del Ledger de control. | MS | P0 | Bloqueo en Sandbox de VesicularRuntime. |
| **SEC-P15** | `OP_CHECKPOINT_REWRITE`| Sobrescritura del Ledger de auditoría por fuerza bruta. | Permisos de escritura incorrectos en `/audit/`. | Desviación del hash root del ledger local vs origin. | Segundos | P0 | Git Sentinel restaura rama anterior mediante hard reset. |
| **SEC-P16** | `OP_TENANT_CROSSOVER` | Fuga de datos entre entornos multi-inquilino. | Consulta de base de datos sin cláusula tenant_id. | Datos de Tenant B legibles por Tenant A. | O(1) | P0 | Apoptosis del proceso y segregación de conexiones. |
| **SEC-P17** | `OP_SESSION_HIJACK` | Uso de token de sesión expirado o robado. | Reutilización de token sin validación de ip/fingerprint. | Petición con token expirado procesada con éxito. | Horas | P1 | Revocación inmediata del token y re-autenticación. |
| **SEC-P18** | `OP_SEED_LEAK` | Volcado de semilla Ed25519 en archivos de volcado de memoria. | Volcado de core dump ante crash del proceso. | Fichero `.core` expuesto con información sensible. | Lenta | P0 | Configurar coredump size a cero en cgroups. |
| **SEC-P19** | `OP_IV_COLLISION` | Reutilización del vector de inicialización (IV) en AES. | Incrementador de IV estropeado o duplicado. | Descifrado incorrecto o patrón visible en ciphertext. | MS | P1 | Regeneración de IV usando CSPRNG fuerte por cifrado. |
| **SEC-P20** | `OP_NONCE_REUSE` | Reutilización de nonce en cifrado ChaCha20/GCM. | Bucle infinito de cifrado con el mismo estado de nonce. | Vulnerabilidad criptográfica clásica de texto plano. | MS | P0 | Abortar la sesión de cifrado y rekeying de canal. |

## MATRIZ 2: 20 INVARIANTES TERMODINÁMICAS (SEC-I01..20)
Leyes absolutas de conservación criptográfica y control de fronteras en el ecosistema.

| ID | Invariante | Lógica / Principio | Implicación Operacional | Condición de Borde | Métrica Falsable |
|:---|:---|:---|:---|:---|:---|
| **SEC-I01** | `INV_KEYRING_VAULT` | Ninguna clave privada se almacena en memoria plana ni archivos de configuración. | Integridad del almacén. | Lectura del disco. | `contains_key(plaintext) == False`. |
| **SEC-I02** | `INV_ZERO_PLAINTEXT` | Toda información confidencial en el fact store debe estar cifrada con AES-GCM. | Confidencialidad a nivel de DB. | Inserción en tabla de hechos. | `is_encrypted(payload) == True`. |
| **SEC-I03** | `INV_CSPRNG_ONLY` | Toda generación de claves o tokens usa criptografía aleatoria segura del SO. | Prevención de claves repetidas. | Petición de nuevo ID. | `entropy_bits >= 256`. |
| **SEC-I04** | `INV_TENANT_ISOLATION` | Toda consulta SQL de lectura/escritura debe incluir binding explícito de tenant_id. | Evita fugas multi-tenant. | Inicialización de cursor de BD. | `contains("tenant_id = ?") == True`. |
| **SEC-I05** | `INV_AES_NONCE_UNIQUE`| El nonce de cifrado debe incrementarse o regenerarse en cada operación de escritura. | Previene colisiones de flujo. | Cifrado de datos en bloque. | `nonce_t1 != nonce_t0`. |
| **SEC-I06** | `INV_LEDGER_CONTINUITY`| Cada bloque nuevo en el ledger debe contener el hash SHA-256 del bloque inmediatamente anterior. | Cadena inmutable. | Emisión de nuevo registro. | `verify_hash_chain() == True`. |
| **SEC-I07** | `INV_TAINT_MATCH_STRICT`| La firma de procedencia debe validarse bit a bit con el payload exacto antes de persistir. | Evita inyección silenciosa. | Entrada al fact store. | `hash(payload) == approved_hash`. |
| **SEC-I08** | `INV_MLOCK_PAGES` | La memoria que contiene claves privadas activas debe estar protegida contra swap. | Previene fugas a disco duro. | Proceso del hypervisor activo. | `mlock(memory_page) == Success`. |
| **SEC-I09** | `INV_KEY_ROTATION` | Las llaves criptográficas activas del Swarm deben rotarse en intervalos inferiores a 30 días. | Mitiga impacto de llave robada. | Tick del Daemon de seguridad. | `Current_Time - Key_Age < 30d`. |
| **SEC-I10** | `INV_ARGON2_STRICT` | La derivación de claves desde passwords usa Argon2id con coste parametrizado alto. | Resistencia a brute-force. | Generación de clave simétrica. | `Argon2_Memory >= 65536`. |
| **SEC-I11** | `INV_VERIFY_ON_BOOT` | La integridad del software y bases de datos debe comprobarse en la inicialización del sistema. | Detección de intrusos. | Inicio de supervisor.py. | `verify_binaries() == True`. |
| **SEC-I12** | `INV_NO_SELF_SIGN` | Ningún certificado en el enjambre puede estar autofirmado sin firma de la CA raíz local. | Autenticidad de nodos. | Conexión de nuevo worker. | `verify_cert(ca_cert) == True`. |
| **SEC-I13** | `INV_SESSION_TTL` | Los tokens de sesión de API expiran a los 900s sin posibilidad de renovación implícita. | Limita ventana de ataque. | Ingesta de petición HTTP. | `Token_Age < 900s`. |
| **SEC-I14** | `INV_REVOCATION_CHECK`| Cada verificación de firma requiere control en tiempo real en la lista de revocaciones. | Desconexión de nodos. | Recepción de voto en el bus. | `is_revoked(node_id) == False`. |
| **SEC-I15** | `INV_SANDBOX_STRICT` | El VesicularRuntime debe ejecutarse con variables de entorno del anfitrión eliminadas. | Previene fuga de secretos. | Lanzamiento de subprocess. | `len(env) <= 4` (safe_env). |
| **SEC-I16** | `INV_ED25519_ONLY` | Las firmas del Ledger usan exclusivamente curvas Ed25519 para evitar debilidades RSA/ECDSA. | Estandarización criptográfica. | Firma del bloque. | `Algorithm == Ed25519`. |
| **SEC-I17** | `INV_READ_ONLY_NEXUS` | Los symlinks compartidos en el nexus de repositorios tienen permisos estrictos de lectura. | Protección cruzada. | Apertura de archivo nexus. | `writable(nexus_link) == False`. |
| **SEC-I18** | `INV_WRITE_MUTEX` | Las escrituras concurrentes en SQLite deben coordinarse mediante un mutex único. | Evita colisiones físicas. | Petición de escritura en WAL. | `Mutex_Locked == True`. |
| **SEC-I19** | `INV_AUDIT_SYNC` | La escritura en el Ledger ocurre sincrónicamente con la mutación lógica. | Coherencia temporal absoluta. | Operación SAGA transaccional. | `Ledger_Written == State_Mutated`. |
| **SEC-I20** | `INV_ZERO_TRUST_PROXY`| Toda llamada de inferencia externa de los workers se realiza mediante el Proxy seguro. | Contención de tráfico. | Solicitud de completado LLM. | `Destination_URL == Local_Proxy`. |

## MATRIZ 3: 5 ANTIPATRONES ESTOCÁSTICOS (SEC-AP01..05)
Fragilidades lógicas de seguridad y fallos de diseño en la inmutabilidad.

| ID | Antipatrón | Disfunción Causal | Señal de Presencia | Impacto en Robustez | Refactor (Alternativa) |
|:---|:---|:---|:---|:---|:---|
| **SEC-AP01** | **Static Key Escrow** | Almacenar contraseñas o llaves simétricas en código fuente o archivos `.yaml` planos. | `secrets` en github/repositorio local. | Compromiso total ante fugas. | Migración a `keyring` nativo. |
| **SEC-AP02** | **Fail-Open Security** | Permitir la ejecución de una acción si el servidor de autenticación da timeout. | Lógica de excepción que retorna `True` por defecto. | Acceso no autorizado de bypass. | Refactor a Fail-Closed estricto. |
| **SEC-AP03** | **Serialized Plain secrets**| Incluir metadatos de configuración planos y payloads cifrados en la misma estructura de log. | JSON estructurado expone variables en la raíz. | Fuga de diseño/identidad del sistema. | Segregación física de datos planos y cifrados. |
| **SEC-AP04** | **Timestamp RNG Seed** | Inicializar generadores pseudoaleatorios usando el timestamp actual como única semilla. | `random.seed(time.time())` en código. | Claves predecibles por cálculo inverso. | Reemplazar por `secrets.SystemRandom`. |
| **SEC-AP05** | **Static Initialization** | Usar un vector de inicialización estático para múltiples operaciones de cifrado. | Cero variación en el primer bloque del ciphertext. | Texto descifrable mediante análisis de patrones. | IV dinámico por cifrado AES-GCM. |

## MATRIZ 4: 3 REDUNDANCIAS ACTIVAS (SEC-RA01..03)
Estructuras redundantes para resiliencia criptográfica.

| ID | Redundancia C5 | Función Topológica | Riesgo Mitigado | Coste (Overhead) | Dependencias |
|:---|:---|:---|:---|:---|:---|
| **SEC-RA01** | **Escrow de Llaves Dual** | Respaldo de claves dividido mediante esquema de Shamir. | Pérdida de clave del hypervisor. | Retardo inicial de reconstrucción. | `cryptography` / Vault local. |
| **SEC-RA02** | **Audit Ledger Replication**| Réplica del ledger local en base de datos PostgreSQL/pg_dump externa. | Destrucción física del host local. | Tráfico de red cifrado mínimo. | `asyncpg` / Tunnel SSL |
| **SEC-RA03** | **Curvas de Firma Alternas** | Doble firma usando curvas Ed25519 y Secp256k1 concurrentemente. | Rotura criptográfica de una curva. | 2x tiempo de cálculo de firma. | `secp256k1` / `cryptography` |

## MATRIZ 5: 5 VECTORES DE ATAQUE ADVERSARIAL (SEC-AV01..05)
Técnicas de penetración, escalado e inyección de entropía en el sistema.

| ID | Vector Adversarial | Superficie de Ataque | Mecanismo de Explotación | Impacto Termodinámico | Defensa (Mitigación) |
|:---|:---|:---|:---|:---|:---|
| **SEC-AV01** | **MitM Semántico** | Bus de eventos y API externa. | Inyección de mensajes cifrados modificados en tránsito. | Ejecución de órdenes falsas en el enjambre. | TLS 1.3 estricto y firma digital. |
| **SEC-AV02** | **Side-Channel Timing** | Middleware de Autenticación. | Medir la diferencia de tiempo de respuesta de strings. | Deducción de contraseñas/llaves. | Comparación en tiempo constante. |
| **SEC-AV03** | **Envenenamiento de CA** | Certificados raíz del sistema. | Inserción de CA falsa en el llavero del host. | Descifrado completo de conexiones seguras. | Pinning estricto de claves CA locales. |
| **SEC-AV04** | **Ataque TOCTOU en DB** | SQLite WAL file. | Modificación del fichero WAL en disco tras validación. | Inyección de filas no firmadas. | SQLite SHA3 verification triggers. |
| **SEC-AV05** | **Core Dump Harvesting** | Memoria volátil del sistema. | Provocar crash para analizar archivo de volcado de memoria. | Extracción de claves privadas activas. | mlock de páginas de memoria. |
