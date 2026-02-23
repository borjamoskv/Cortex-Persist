# 🧠 CORTEX v5.0 — Neural-Bandwidth Sync (Zero-Latency Intent Ingestion)

> **Documento Soberano: Arquitectura de Ingesta Neural**
> Define la infraestructura de telepatía simulada (Neural Sync) que mapea el contexto implícito del sistema operativo a la "intención" del usuario antes de que este formule una petición.

---

## 🏗️ 1. Arquitectura Base (Desacoplada)

El sistema **Neural-Bandwidth Sync** se apoya en un bucle asíncrono e independiente (`_run_neural_loop`) que forma parte del demonio de MOSKV-1 (`MoskvDaemon`). 
A diferencia de los monitores pesados (ej. disco o bases de datos) que se ejecutan cada 300 segundos, el Neural Sync mantiene un muestreo agresivo de **1Hz (1 vez por segundo)**.

**¿Por qué desacoplado?**
Para evitar bloquear el *event loop* del demonio principal. Si un rastreo neural demora u ocupa recursos del disco, aislar este bucle previene la falla en cascada (*Cascading Failure*) que mataría a los demás monitores críticos.

## ⚡ 2. Zero-Latency Sensors (Sensores PyObjC)

Originalmente, los sensores del sistema leían el estado de macOS usando subprocesos costosos (`osascript` para leer ventanas y `pbpaste` para leer el portapapeles). 
Bajo el estándar MEJORAlo 130/100, estos se refactorizaron a llamadas nativas usando **PyObjC**:

1. **`ActiveWindowSensor`**: Utiliza `AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()` para detectar milimétricamente el cambio de ventana activa.
2. **`ClipboardSensor`**: Utiliza `AppKit.NSPasteboard.generalPasteboard().stringForType_()` para capturar trazas de error, links o textos instantáneamente.

**Impacto:** Se pasa de consumir más de ~100ms y crear procesos zombi, a resolverse nativamente en `< 1ms`, permitiendo la ingesta pasiva de manera completamente "invisible" (UX sin impacto de batería).

## 🔮 3. Motor de Inferencia Causal (`NeuralIntentEngine`)

Cuando el bucle `1Hz` capta un cambio sustancial (*deduplicado* para no ahogar los logs), el `NeuralIntentEngine` ejecuta heurísticas para deducir la **hipótesis de intención**.

**Reglas de Inferencia (Heurísticas Actuales):**
* **DEBUGGING**: App (`Cursor`|`Terminal`) + Portapapeles con *Error/Traceback* → Asume intención de `debugging_error`.
* **INVESTIGACIÓN**: App de Navegación (`Chrome`|`Arc`) + Portapapeles con una *URL* → Asume intención de `researching`.
* **ARQUEOLOGÍA / DEUDA TÉCNICA**: App de Código (`Cursor`|`VSCode`) + Portapapeles con un *TODO/F_IXME/H_ACK* → Asume intención de `technical_debt_focus`.
* **PLANIFICACIÓN**: App Organizacional (`Linear`|`Notion`) + Portapapeles con estructura de ticket → Asume intención de `planning`.

## 🔄 4. Deduplicación Temporal de Intenciones

El motor incorpora una lógica de retención dinámica por *60 segundos* (`_last_hypothesis_timestamp`). Si el demonio infiere la misma intención que el ciclo anterior y no ha pasado un minuto, el trigger se ahoga de manera silenciosa para no desbordar los canales de notificación de macOS.
