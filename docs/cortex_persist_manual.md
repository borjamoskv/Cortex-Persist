# CORTEX Persist — Manual de Instrucciones y Guía del Usuario
**Versión del Sistema:** 0.3.0b3  
**Arquitectura:** Local-First / Híbrida C5-REAL  
**Estado:** Estable / Producción  
**Alineación:** Nueve Leyes del Substrato CORTEX  

---

## 📖 Tabla de Contenidos
1. [Introducción y Postura Epistémica (La Analogía del Aeropuerto)](#1-introducción-y-postura-epistémica-la-analogía-del-aeropuerto)
2. [Arquitectura del Sistema y Flujos de Señal](#2-arquitectura-del-sistema-y-flujos-de-señal)
3. [El Contrato del Write-Path (Patrón Saga en Detalle)](#3-el-contrato-del-write-path-patrón-saga-en-detalle)
4. [El Contrato del Read-Path (Aislamiento y Taint)](#4-el-contrato-del-read-path-aislamiento-y-taint)
5. [Guía de Inicio Rápido (Los Primeros 5 Minutos)](#5-guía-de-inicio-rápido-los-primeros-5-minutos)
6. [Interfaz de Línea de Comandos (CLI) - Manual Completo](#6-interfaz-de-línea-de-comandos-cli---manual-completo)
7. [Referencia de API REST (Endpoints & Payloads)](#7-referencia-de-api-rest-endpoints--payloads)
8. [Integración MCP (Model Context Protocol) para Agentes](#8-integración-mcp-model-context-protocol-para-agentes)
9. [Seguridad, Criptografía y Gestión de Claves](#9-seguridad-criptografía-y-gestión-de-claves)
10. [Capacidades Exclusivas (¿Por qué CORTEX y no Postgres/Qdrant?)](#10-capacidades-exclusivas-por-qué-cortex-y-no-postgresqdrant)
11. [Casos de Uso Guiados (Tutoriales Paso a Paso)](#11-casos-de-uso-guiados-tutoriales-paso-a-paso)
12. [Tabla Forense de Firmas de Fallo y Recuperación de Desastres](#12-tabla-forense-de-firmas-de-fallo-y-recuperación-de-desastres)

---

## 1. Introducción y Postura Epistémica (La Analogía del Aeropuerto)

En la informática tradicional, las bases de datos asumen que **el cliente tiene la razón**: si el código de tu aplicación envía un comando `INSERT`, la base de datos escribe los bytes en el disco sin chistar. 

En la era de los agentes autónomos de IA, esta asunción es **catastrófica**. Los modelos de lenguaje grandes (LLMs) operan mediante probabilidades, no certezas. Alucinan, pueden ser manipulados mediante inyecciones de prompts (jailbreaks) y carecen de un sentido de permanencia determinista. 

**CORTEX Persist cambia las reglas de juego.** Opera bajo una postura epistémica de desconfianza radical: **el output de un LLM es una conjetura probabilística hasta que se demuestre lo contrario en una frontera determinista.**

### 🛃 La Analogía del Aeropuerto Internacional

Para entender CORTEX Persist de forma intuitiva, imagine el sistema como el control de seguridad de un aeropuerto internacional de máxima seguridad:

1.  **La Propuesta Generativa (El Pasajero):** El LLM propone un cambio de estado o una escritura en base de datos. Este pasajero es sospechoso por defecto.
2.  **Ingress Guards (Control de Pasaportes y Escáner de Equipaje):** La propuesta pasa por filtros rígidos y deterministas que analizan si lleva credenciales expuestas, comandos inyectados o contenido que viola la seguridad de aislamiento. Si falla el control, el pasajero es rechazado inmediatamente (**SAGA-1**).
3.  **Taint Engine (Marcador Químico invisible):** Al pasar, se le inyecta un tinte invisible pero permanente en su pasaporte (`CORTEX-TAINT`). Si este pasajero corrompe algo más tarde, el tinte nos dirá exactamente de dónde vino y quién lo autorizó.
4.  **Saga Orchestrator (El Protocolo de Embarque):** El pasajero avanza en fila. Si en la puerta de embarque no hay asientos libres o hay un fallo técnico, se cancela el vuelo y el pasajero es escoltado de vuelta a la salida, revirtiendo cada paso de forma ordenada (Compensación Saga).
5.  **Master Ledger (La Caja Negra del Avión):** Una vez dentro, cada movimiento queda registrado en un registro inmutable encadenado criptográficamente por hash blocks. Si alguien intenta alterar la caja negra en tierra, la firma digital se rompe inmediatamente y el avión se bloquea.

---

## 2. Arquitectura del Sistema y Flujos de Señal

El sistema está diseñado de forma modular. La CPU ejecuta la orquestación lógica en Python, mientras que los motores de encriptación, validación de firmas vectoriales y hash-chains actúan como núcleos inmutables y de alto rendimiento.

### Diagrama de Secuencia de Escritura (Write-Path)

```mermaid
sequenceDiagram
    autonumber
    participant A as Agent / LLM
    participant S as Saga Orchestrator
    participant G as Ingress Guards
    participant L as Master Ledger
    participant D as SQLite / DB
    participant V as Vector Index

    A->>S: Proponer Escritura (Fact Proposal)
    activate S
    S->>G: Validar Heurística & Reglas (SAGA-1)
    G-->>S: Aprobado (Clean)
    S->>S: Generar & Estampar CORTEX-TAINT (SAGA-2)
    S->>S: Validar Esquema JSON (SAGA-3)
    S->>S: Encriptar Datos Sensibles (SAGA-4)
    S->>L: Registrar Transacción de Auditoría (SAGA-5)
    L-->>S: Hash Confirmado
    S->>D: Escribir Registro en SQLite (SAGA-6)
    S->>V: Indexar Embeddings Vectoriales (SAGA-7)
    V-->>S: Completado
    S-->>A: Retornar Fact ID + Transaction Hash
    deactivate S
```

*Si ocurre un error en el paso 7, la Saga activa en orden inverso las compensaciones: elimina el índice vectorial (7), revierte la escritura en SQLite (6), anula el hash del ledger (5), destruye claves efímeras (4) y registra el aborto de la transacción en la auditoría.*

---

## 3. El Contrato del Write-Path (Patrón Saga en Detalle)

Toda transacción en CORTEX Persist implementa el patrón **Saga**. Esto asegura que las escrituras sean consistentes incluso si se ejecutan a través de múltiples servicios descentralizados o bases de datos híbridas.

```python
# Ejemplo Conceptual de la Lógica Interna de la Saga en CORTEX
async def execute_cortex_write_saga(fact_proposal: FactProposal) -> FactResult:
    steps_executed = []
    try:
        # SAGA-1: Ingress Guards
        await run_ingress_guards(fact_proposal)
        steps_executed.append("GUARDS")
        
        # SAGA-2: Taint Stamp
        taint_token = generate_taint_token(fact_proposal)
        fact_proposal.metadata["cortex-taint"] = taint_token
        steps_executed.append("TAINT")
        
        # SAGA-3: Schema Validation
        validate_json_schema(fact_proposal.content, fact_proposal.schema)
        steps_executed.append("SCHEMA")
        
        # SAGA-4: Encryption
        encrypted_payload = encrypt_payload(fact_proposal.sensitive_data)
        steps_executed.append("ENCRYPT")
        
        # SAGA-5: Ledger Block
        ledger_block = await append_to_ledger(fact_proposal, taint_token)
        steps_executed.append("LEDGER")
        
        # SAGA-6: DB Write
        fact_id = await write_to_sqlite(fact_proposal, encrypted_payload)
        steps_executed.append("SQLITE")
        
        # SAGA-7: Vector Sync
        await index_vector_embedding(fact_id, fact_proposal.content)
        return FactResult(status="committed", fact_id=fact_id, tx_hash=ledger_block.hash)
        
    except Exception as e:
        await rollback_write_saga(steps_executed, fact_proposal)
        raise SagaTransactionAborted(f"Saga abortada en {steps_executed[-1]}: {str(e)}")
```

### Ingress Guards: Los 11 Patrones de Seguridad
Los Guards escanean proactivamente el contenido propuesto antes de tocar el disco. Si el contenido coincide con alguno de los siguientes 11 patrones, la transacción aborta automáticamente:
1.  Claves privadas de criptografía asimétrica (`-----BEGIN RSA PRIVATE KEY-----`, etc.).
2.  Tokens de acceso de GitHub (patrón `ghp_[a-zA-Z0-9]{36}`).
3.  Claves de API de AWS (`AKIA[0-9A-Z]{16}`).
4.  Secrets de AWS Client (`[a-zA-Z0-9+/]{40}`).
5.  Tokens secretos de Slack (`xoxb-`, `xoxp-`).
6.  Claves privadas de Ethereum (hexadecimales puras de 64 caracteres asociadas a firmas ECDSA).
7.  Fórmulas matemáticas corruptas o infinitas en formato LaTeX para evitar DoS por parseo.
8.  Intentos de inyección SQL mediante secuencias de escape de SQLite.
9.  Rutas absolutas del sistema operativo del host (ej. `/etc/passwd` o `/Users/.../CloudDocs`).
10. Tokens de Stripe (`sk_live_...`).
11. Credenciales de Base de Datos en cadenas de conexión estructuradas (`postgresql://`).

---

## 4. El Contrato del Read-Path (Aislamiento y Taint)

A diferencia de las consultas relacionales clásicas, el Read-Path en CORTEX Persist está atado a dos invariantes de seguridad:

### 4.1 Aislamiento de Inquilino Estricto (Tenant Isolation)
El motor de consulta requiere obligatoriamente un parámetro `tenant_id`. Si una consulta intenta ejecutarse sin este ámbito, la base de datos devuelve una excepción de violación de acceso P0.
*   **A nivel físico:** Las tablas contienen particiones lógicas por ID de inquilino.
*   **A nivel de red:** El MCP Server valida el contexto del agente solicitante y restringe la consulta únicamente al espacio de nombres autorizado para ese ID de agente.

### 4.2 Propagación Viral de Taint (Taint Propagation)
Cuando lees un hecho que fue escrito por un agente estocástico (identificado con el flag `tainted=True`), la API no solo te entrega el contenido, sino que **arrastra el marcador de taint en la cabecera de la respuesta.**
*   Si el Agente B lee el Hecho 1 (tainted) y genera el Hecho 2 a partir de esa lectura, el Hecho 2 **hereda automáticamente la firma de taint original**, construyendo un árbol de procedencia y linaje cognitivo.
*   Esto previene el "lavado de alucinaciones", donde datos generados por un modelo erróneo se hacen pasar por hechos válidos y limpios tras ser re-procesados.

---

## 5. Guía de Inicio Rápido (Los Primeros 5 Minutos)

### Paso 1: Instalación del Entorno
Instale el paquete en modo desarrollo con todas las dependencias locales de almacenamiento y criptografía:

```bash
cd /Users/borjafernandezangulo/10_PROJECTS/cortex-persist
pip install -e ".[all]"
```

### Paso 2: Inicialización de la Base de Datos
Corra el asistente de aprovisionamiento para crear el archivo local SQLite y las tablas del ledger transaccional:

```bash
cortex status
```
*Si la base de datos no existe, se creará automáticamente en la ruta por defecto: `~/.cortex/cortex.db`.*

### Paso 3: Almacenar tu Primer Hecho
Proponga un registro en la base de datos. Observe cómo se valida, encripta y commits en una sola operación controlada:

```bash
cortex store --content "La API externa devolvió estado 200 a las 10:15" --source "monitoring-agent" --tags "api,status"
```

**Salida Esperada en Consola:**
```json
{
  "fact_id": "f_01JHG56YTR782KSM982361HJKP",
  "transaction_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "status": "committed",
  "taint_applied": "taint:monitoring-agent:session_xyz:2026-05-19T08:38:00Z"
}
```

---

## 6. Interfaz de Línea de Comandos (CLI) - Manual Completo

### `cortex store`
Escribe información en el sistema.
*   `--content <texto>`: (Requerido) El cuerpo del hecho.
*   `--source <nombre>`: (Requerido) Identificador del agente emisor.
*   `--tags <tag1,tag2>`: Categorización para búsquedas rápidas.
*   `--tenant <id>`: Define el inquilino (por defecto: `tenant-default`).
*   `--sensitive`: Si se activa, cifra el contenido usando la clave AES local de la máquina antes de escribir.

### `cortex search`
Consulta la base de datos semántica mediante embeddings locales.
*   `--query "<texto>"`: Frase de búsqueda.
*   `--limit <número>`: Cantidad de resultados (por defecto: 5).
*   `--threshold <float>`: Filtro de similitud coseno mínima (ej: `0.75`).

### `cortex ledger verify`
Analiza la integridad del ledger de extremo a extremo. Recorre todos los bloques de transacciones recalculando los hashes encadenados y contrastándolos con la raíz Merkle.
*   Si el ledger es válido, retorna exitosamente con código de salida `0`.
*   Si se detecta cualquier alteración física de un byte en la base de datos, el comando falla con código de error `1102` y emite una alerta estructurada de desastre.

---

## 7. Referencia de API REST (Endpoints & Payloads)

El servidor FastAPI expone una API REST robusta para integración con microservicios externos.

### `POST /v1/store`
*   **Headers:**
    *   `Content-Type: application/json`
    *   `X-Cortex-Origin-Signature: <firma_ed25519>`
*   **Cuerpo (Payload):**
    ```json
    {
      "content": "Contrato firmado con cliente ID 992",
      "source": "sales-agent",
      "tenant_id": "tenant-corp",
      "sensitive": true,
      "metadata": {
        "version": "1.0",
        "ip_address": "192.168.1.45"
      }
    }
    ```
*   **Respuesta Exitosa (201 Created):**
    ```json
    {
      "success": true,
      "data": {
        "fact_id": "f_sales_01JHG",
        "tx_hash": "bc826ad...",
        "block_height": 402,
        "created_at": "2026-05-19T08:38:00.123Z"
      }
    }
    ```

---

## 8. Integración MCP (Model Context Protocol) para Agentes

CORTEX Persist se integra directamente con el protocolo MCP. Esto permite que agentes de IA (como Claude en Desktop o Cursor) invoquen de forma nativa herramientas de almacenamiento y consulta en base a su contexto de conversación.

### Flujo de Trabajo en Claude Desktop

Cuando el agente necesita recordar algo de la conversación actual, no lo escribe en memoria volátil. Invoca la herramienta `cortex_store`:

```json
{
  "name": "cortex_store",
  "arguments": {
    "content": "El usuario prefiere el puerto de desarrollo 8080 en lugar del 8484",
    "source": "antigravity-agent",
    "tags": ["preferencias", "configuracion"]
  }
}
```

La respuesta de la herramienta confirma al agente que el hecho ha cruzado los Ingress Guards y ya está registrado criptográficamente en el ledger inmutable local.

---

## 9. Seguridad, Criptografía y Gestión de Claves

Para garantizar que el ledger sea realmente **Tamper-Evident**, CORTEX utiliza primitivas criptográficas avanzadas implementadas mediante aceleración nativa:

```mermaid
graph LR
    Payload[Payload del Hecho] --> Hash[SHA3-256]
    Hash --> BlockHash[Hash del Bloque Anterior]
    BlockHash --> EdSignature[Firma Ed25519 del Agente]
    EdSignature --> LedgerBlock[Bloque de Ledger Inmutable]
```

1.  **Firma del Agente (Ed25519):** Todo agente emite un mensaje firmado con su clave privada local. CORTEX valida esta firma contra su registro de claves públicas autorizadas. Si un agente no registrado intenta escribir, la transacción se aborta de inmediato.
2.  **Cifrado en Reposo (AES-GCM-256):** Los campos marcados como sensibles se cifran en memoria antes de escribirse en el disco. La clave de cifrado maestro se almacena en el llavero seguro del sistema operativo (`keyring` en macOS/Linux), garantizando que si un atacante copia el archivo de base de datos `cortex.db`, no pueda leer los datos sensibles.
3.  **Rotación de Claves de Seguridad:**
    *   Ejecute `cortex keys rotate` para invalidar las claves viejas y migrar de forma segura la clave maestra del llavero.
    *   Este proceso genera una entrada de auditoría inmutable en el ledger del sistema.

---

## 10. Capacidades Exclusivas (¿Por qué CORTEX y no Postgres/Qdrant?)

A diferencia de una base de datos tradicional, CORTEX Persist está construida específicamente para el ciclo de vida de los agentes autónomos:

| Característica | Base de Datos Convencional (Postgres) | Base Vectorial Pura (Qdrant) | CORTEX Persist |
| :--- | :--- | :--- | :--- |
| **Filtro de Alucinaciones** | No. Acepta cualquier string. | No. Indexa cualquier vector. | **Sí. Bloquea si no pasa Guards de Admisión.** |
| **Linaje Causal** | Relaciones de clave foránea simples. | Búsqueda por similitud espacial. | **Hash-chain continuo con firma digital de procedencia.** |
| **Detección de Fugas** | No. Permite commits con secretos. | No. Indexa secretos en vectores. | **Sí. Detección heurística de 11 firmas de credenciales.** |
| **Aislamiento de Agentes** | Requiere lógica compleja en App. | Requiere colecciones separadas. | **Nativo por tenant con herencia viral de Taint.** |
| **Auditoría Legal (EU Act)** | Requiere logs externos vulnerables. | No aplica. | **Integrado en Ledger C5-REAL autocomprobable.** |

---

## 11. Casos de Uso Guiados (Tutoriales Paso a Paso)

### Tutorial 1: Auditoría de Decisiones en Cumplimiento de la EU AI Act
**Objetivo:** Crear un registro inalterable que demuestre ante reguladores por qué un agente autónomo de decisiones de inversión compró acciones de la empresa X en lugar de Y.

1.  El agente procesa los datos del mercado y propone la transacción a CORTEX:
    ```bash
    cortex store --content "Orden de compra: 100 ACCIONES de AAPL. Justificación: Incremento de margen operativo del 12%" --source "investment-agent-v1" --tags "trade,compliance" --sensitive
    ```
2.  El sistema encripta los datos y añade la firma de procedencia criptográfica.
3.  Dos semanas después, el auditor corre la verificación legal:
    ```bash
    cortex ledger verify
    ```
4.  CORTEX devuelve el reporte firmado. El auditor puede exportar el bloque de la transacción demostrando matemáticamente que el registro no ha sido alterado desde el segundo exacto en que el agente tomó la decisión.

---

## 12. Tabla Forense de Firmas de Fallo y Recuperación de Desastres

Use esta guía para identificar y resolver de forma proactiva fallas de integridad en la infraestructura de persistencia:

| Firma de Fallo (Mensaje de Error) | Causa Probable | Severidad | Acción Correctiva de Emergencia |
| :--- | :--- | :--- | :--- |
| `LEDGER_DISCONTINUITY_ERROR (Code 1102)` | Un proceso externo o atacante ha modificado directamente el archivo SQLite `cortex.db` alterando el histórico. | **CRÍTICA (P0)** | 1. Detener demonios de agente.<br>2. Ejecutar `cortex ledger restore --checkpoint <hash>` para restaurar desde la copia de respaldo Merkle en la nube o disco frío.<br>3. Investigar brecha de permisos del sistema host. |
| `INGRESS_GUARD_VIOLATION: Pattern Match #3`| El agente intentó persistir datos que contenían claves de acceso de AWS. | MEDIA | 1. Modificar el prompt del agente para sanitizar variables.<br>2. Rotar la clave de AWS expuesta de inmediato por motivos de seguridad. |
| `TENANT_ACCESS_VIOLATION` | Un hilo de agente intentó realizar una búsqueda de datos sin proveer su `tenant_id` en las cabeceras. | **CRÍTICA (P0)** | 1. Auditar el código del agente de origen.<br>2. Comprobar que no haya fugas de datos inter-inquilino en la sesión actual. |
| `TAINT_SIGNATURE_MISSING` | Una propuesta de escritura evadió la fase SAGA-2 de inyección de metadatos de taint. | ALTA | 1. Verificar si el SDK del cliente asíncrono está actualizado.<br>2. Asegurar que las llamadas de persistencia pasen obligatoriamente por el `sage_orchestrator`. |
| `KEYRING_DECRYPTION_FAILED` | La clave maestra AES guardada en el llavero del sistema operativo host no coincide con la base de datos local. | ALTA | 1. Verificar si cambió la sesión de usuario del sistema operativo host.<br>2. Ejecutar `cortex keys test-connection` para validar credenciales de llavero. |
