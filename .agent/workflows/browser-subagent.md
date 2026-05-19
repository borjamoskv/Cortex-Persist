---
description: Workflow maestro para browser_subagent — QA visual, investigación web, testing de flujos y scraping inteligente
---

# 🌐 Browser Subagent — Protocolo de Ejecución Soberana v2.0

> **Substrato Cognitivo:** CORTEX Unified Substrate (v6.0)
> **Directiva Primaria:** Tratar la interacción en navegador como una propuesta estocástica y forzar fronteras deterministas de validación (C5-REAL).

---

## 1. 🌌 Postura Epistémica: El Navegador como Caja de Arena Estocástica

El navegador es una interfaz visual propensa a la entropía (cambios de DOM, timeouts, bloqueos por bots, latencia de red). Este workflow reduce la fricción y la latencia cognitiva aplicando las siguientes reglas:

1. **Aislamiento de Taint:** Toda sesión de navegador iniciada para extraer datos de terceros debe heredar y conservar el flag `CORTEX-TAINT` en sus reportes.
2. **C5-REAL Verification:** Ninguna acción en el navegador se considera completada sin una verificación determinista posterior (lectura directa del DOM resultante o captura de pantalla).
3. **Evidencia por Grabación:** Todas las sesiones generan grabaciones WebP automáticas. El nombre de grabación (`RecordingName`) debe mapearse de forma unívoca a la tarea para facilitar auditorías forenses.

---

## 2. ⚡ Matriz de Decisiones Termodinámicas (Exergía de Red)

No inicies el subagente de navegador si puedes resolver la tarea con primitivas más baratas:

| Canal | Método alternativo | Caso de Uso | Exergía (Tokens/Tiempo) |
| :--- | :--- | :--- | :--- |
| **Contenido Estático** | `read_url_content` | Páginas de documentación, markdown, JSONs estáticos. | MÍNIMA (1x) |
| **Búsqueda Web** | `search_web` | Preguntas de actualidad, APIs, documentación externa. | BAJA (2x) |
| **Interacción Dinámica** | **`browser_subagent`** | Páginas Single Page App (SPA), logins con JS, flujos de checkout, QA visual. | MÁXIMA (20x) |

---

## 3. 🔄 El Ciclo de Interacción Determinista (Saga del Navegador)

Para evitar bucles infinitos de reintento, cada interacción debe seguir este contrato de ejecución:

```text
[Definición de Tarea]
        ↓
[Pre-Vuelo HTTP] (Confirmar puerto/resolución local si aplica)
        ↓
[Navegación Inicial] → (SAGA-1: Timeout / DNS Failure → Abortar)
        ↓
[Espera de Estabilidad] (Espera a red o elemento clave en el DOM)
        ↓
[Bucle de Interacción] (Clicks, inputs usando selectores robustos)
        ↓
[Assert de Estado] (Confirmar cambio de URL o presencia de elemento éxito)
        ↓
[Extracción / Captura] (Volcado de datos estructurados + Screenshot final)
```

---

## 4. 🎯 Jerarquía de Selectores Anti-Fragilidad

Cuando definas tareas en `Task`, instruye al subagente a usar la siguiente jerarquía de búsqueda de elementos:

1. **ID Único:** `[id="submit-button"]` (Inmutable).
2. **Atributo Semántico:** `[data-testid="login-input"]` or `[aria-label="Search"]`.
3. **Text Anchor:** Buscar por texto exacto del botón/enlace (ej. "Save Changes").
4. **CSS Predictivo:** `.btn-primary` (Evitar rutas largas del tipo `div > div > ul > li:nth-child(2) > a`).

---

## 5. Plantillas de Tareas Altamente Optimizadas

### 5.1 QA Visual y Consola (Entorno Local)
```yaml
TaskName: "QA Visual Local"
RecordingName: "qa_visual_local"
Task: |
  Navigate to http://localhost:5173
  
  Verify and report:
  1. The page loads without throwing uncaught exceptions in the console.
  2. The primary heading (h1) matches "[TITLE]".
  3. All images in the main grid load (no 404s or broken assets).
  4. Compare typography and layout alignment against #0A0A0A base styling.
  
  Return when elements are verified.
  In your final report, include:
  - Exact console logs (errors and warnings).
  - Status of each image tested.
  - Performance impression (TTFT/LCP visual estimation).
```

### 5.2 Test de Flujo de Usuario y Autenticación
```yaml
TaskName: "Auth Flow Test"
RecordingName: "user_auth_flow"
Task: |
  Navigate to [URL]
  
  Execute the following actions:
  1. Locate the username field and input "[USER]".
  2. Locate the password field and input "[PASSWORD]".
  3. Click the button with the text "Sign In" or "Log In".
  4. Wait for redirection. The target URL must contain "[DASHBOARD_PATH]".
  5. Verify the existence of a profile indicator or sign-out button.
  
  Abort immediately if a validation warning appears.
  Return when the dashboard is visible.
  In your final report, include:
  - Redirection timeline (initial URL to dashboard URL).
  - Verification of the profile element.
  - Any error screens encountered.
```

### 5.3 Extracción de Datos Estructurados (Scraping Dinámico)
```yaml
TaskName: "Dynamic Scraping"
RecordingName: "dynamic_scrape"
Task: |
  Navigate to [URL]
  
  Extract the following attributes:
  1. Item Title (Selector: `[data-field="title"]` or similar).
  2. Item Price (Selector: `.price` or text containing "$").
  3. Click "Next Page" (Selector: `[aria-label="Next"]`) and repeat the extraction.
  
  Return when page 2 extraction completes.
  In your final report, format the output as a clean Markdown table with keys:
  - title
  - price
  - url
```

### 5.4 Multi-Viewport y Responsividad
```yaml
TaskName: "Responsive QA"
RecordingName: "responsive_qa"
Task: |
  Navigate to [URL]
  
  Perform tests at:
  1. Desktop (1920x1080): Verify sidebar is expanded and links are visible.
  2. Mobile (375x812): Verify sidebar collapses into a hamburger menu. Click menu to verify expand behavior.
  
  Return when both viewports are checked.
  In your final report, include:
  - Visual anomalies (content clipping, overlapping text).
  - Element interaction status on mobile.
```

---

## 6. 🚨 Signaturas de Fallo en Navegación (Auditoría Forense)

Si observas estos comportamientos durante la ejecución, detén el bucle y ejecuta la remediación correspondiente:

| Síntoma | Causa probable | Remediación C5-REAL |
| :--- | :--- | :--- |
| **Timeout de red (30s+)** | Puerto local no levantado o CORS estricto. | Detener, ejecutar `curl -I [URL]` localmente y verificar logs de consola. |
| **Elemento no interactuable** | Superposición por modal, cookie banner o carga asíncrona tardía. | Añadir paso intermedio: "Click 'Accept' on the cookie banner first" o scroll. |
| **Re-redirección a login** | Falta de persistencia de sesión o expiración de token. | Verificar si se requiere inyectar cookies previas o ejecutar el flujo de login secuencial. |
| **Pantalla en blanco / Crash** | Excepción JS crítica no controlada. | Leer DOM con `read_browser_page` para inspeccionar `<body>` crudo y extraer trazas de error. |

---

## 7. Protocolo de Cierre (Ship Gate Integration)

Una vez completada la llamada de `browser_subagent`:
1. **Verificar el archivo de video:** Asegurar que se haya guardado en el directorio de artifacts asignado.
2. **Inspección de DOM de Cierre:** Realizar una lectura corta del estado final del DOM para consolidar los cambios en el log del Ledger.
3. **Liberar recursos:** Cerrar los servidores de desarrollo levantados temporalmente si ya no son requeridos.
