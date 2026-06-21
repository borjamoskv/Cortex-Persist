<!-- [C5-REAL] Exergy-Maximized -->
---
description: Workflow maestro para browser_subagent — QA visual, investigación web, testing de flujos y scraping inteligente
---

# 🌐 Browser Subagent — Workflow Maestro

## Cuándo usar browser_subagent

| Caso de uso | Ejemplo |
|---|---|
| **QA Visual** | Verificar que una web se ve correcta en diferentes viewports |
| **Testing de flujos** | Login → Dashboard → Checkout funciona end-to-end |
| **Investigación web** | Leer docs, analizar competidores, extraer info de APIs |
| **Scraping inteligente** | Extraer datos estructurados de páginas dinámicas (JS-rendered) |
| **Captura de evidencia** | Grabar vídeo de bugs o comportamientos para documentar |
| **Formularios y auth** | Rellenar formularios, testear autenticación |

## Cuándo NO usar browser_subagent

- **Leer contenido estático** → Usa `read_url_content` (más rápido, sin overhead)
- **Buscar en internet** → Usa `search_web` primero
- **Ver archivos locales** → Usa `view_file`

## Anatomía de una buena llamada

```
browser_subagent(
  TaskName: "Título Legible Corto",        # Max 3-5 palabras
  RecordingName: "nombre_con_underscores",  # Max 3 palabras, lowercase
  Task: "..."                               # El prompt completo (ver abajo)
)
```

### El Task prompt — reglas de oro

El `Task` es un prompt completo para un agente autónomo. Debe ser **autocontenido**:

1. **URL exacta** — Siempre empezar con "Navigate to [URL]"
2. **Acciones paso a paso** — Numerar cada acción concreta
3. **Qué buscar** — Describir qué verificar o extraer
4. **Condición de retorno** — "Return when..." con criterio claro
5. **Qué reportar** — "In your final report, include: [lista]"

## Plantillas por caso de uso

---

### 1. QA Visual de web local

```
Task: |
  Navigate to http://localhost:5173

  Verify the following:
  1. The page loads without console errors
  2. The hero section displays correctly with the title "[TÍTULO]"
  3. Scroll down and verify the gallery section shows at least [N] items
  4. Resize the browser to 375x812 (mobile) and verify responsive layout
  5. Check that all images load (no broken image icons)

  Return when all checks are complete.

  In your final report, include:
  - Pass/fail for each check
  - Any visual issues found
  - Any console errors or warnings
  - Screenshots descriptions of any problems
```

### 2. Testing de flujo de usuario

```
Task: |
  Navigate to [URL]

  Complete the following user flow:
  1. Click on "[BOTÓN/LINK]"
  2. Fill in the form:
     - Field "[NAME]": enter "[VALUE]"
     - Field "[NAME]": enter "[VALUE]"
  3. Click "[SUBMIT BUTTON]"
  4. Wait for the page to load
  5. Verify that [SUCCESS CONDITION]

  If any step fails, stop and report the failure.

  Return when the flow is complete or a failure is detected.

  In your final report, include:
  - Each step attempted and its result
  - The final URL after completion
  - Any error messages displayed
```

### 3. Investigación de competidor/producto

```
Task: |
  Navigate to [URL]

  Analyze the following aspects:
  1. Main value proposition — what does the product claim to do?
  2. Key features listed on the page
  3. Pricing model (if visible)
  4. Tech stack indicators (check footer, source, meta tags)
  5. Design patterns worth noting (animations, layout, interactions)

  Return when analysis is complete.

  In your final report, include:
  - Summary of the product in 2-3 sentences
  - Bullet list of key features
  - Pricing info if found
  - Design/UX observations
  - Any technical observations
```

### 4. Extracción de datos estructurados

```
Task: |
  Navigate to [URL]

  Extract the following data:
  1. [DATO 1] — location: [CSS selector or description]
  2. [DATO 2] — location: [CSS selector or description]
  3. If there is pagination, navigate to page 2 and extract the same data

  Return when all data is extracted.

  In your final report, format the data as:
  - A structured list or table
  - Include the source URL for each data point
```

### 5. Multi-viewport QA

```
Task: |
  Navigate to [URL]

  Test across these viewports:
  1. Desktop: 1920x1080 — verify [CRITERIA]
  2. Tablet: 768x1024 — verify [CRITERIA]
  3. Mobile: 375x812 — verify [CRITERIA]

  For each viewport:
  - Resize the browser window first
  - Wait for layout to settle
  - Check navigation, images, text readability
  - Note any overflow, broken layouts, or hidden elements

  Return when all viewports are tested.

  In your final report, include:
  - Pass/fail per viewport
  - Specific issues found per viewport
  - Overall responsive quality assessment (1-10)
```

## Errores comunes a evitar

| Error | Solución |
|---|---|
| Task vago ("check the page") | Ser específico: qué verificar, dónde, qué esperar |
| Sin condición de retorno | Siempre incluir "Return when..." |
| Sin formato de reporte | Siempre pedir "In your final report, include..." |
| URL incorrecta | Verificar que el servidor está corriendo antes de lanzar |
| Demasiadas acciones | Max 5-7 pasos por subagent. Si necesitas más, dividir en múltiples llamadas |
| No leer el resultado | Después del subagent, SIEMPRE hacer screenshot o leer DOM para verificar |

## Combinaciones potentes

### Browser + QA Chain
```
1. run_command → npm run dev (levantar servidor)
2. browser_subagent → QA visual completo
3. Si falla → editar código → repetir
```

### Browser + Research Swarm
```
1. search_web → encontrar URLs relevantes
2. browser_subagent × N → analizar cada una en paralelo
3. Sintetizar resultados
```

### Browser + Screenshot Evidence
```
1. browser_subagent → testear flujo, el vídeo se graba automáticamente
2. El recording queda en artifacts como evidencia
3. Embedir en walkthrough.md con ![caption](path)
```

## Referencia rápida de RecordingName

- `qa_visual_check` — verificación visual general
- `responsive_test` — test multi-viewport
- `user_flow_test` — test de flujo de usuario
- `competitor_analysis` — análisis de competidor
- `bug_reproduction` — reproducción de bug
- `deploy_verification` — verificación post-deploy
