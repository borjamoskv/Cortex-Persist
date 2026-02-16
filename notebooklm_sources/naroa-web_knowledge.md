# 🧠 CORTEX Domain: NAROA-WEB

## 🔍 NOTAS DE INVESTIGACIÓN (CRÍTICO)
> NotebookLM: He detectado las siguientes lagunas en CORTEX para este proyecto.
- Hay **8** hechos sin verificar que requieren validación lógica.

## Base de Conocimiento
### Knowledge
- **Uses vanilla JS, no framework, Industrial Noir aesthetic** (Confid: stated)
- **Gallery uses chromatic aberration effect on hover** (Confid: stated)
- **Infinite Zoom feature implemented using OpenSeadragon Deep Zoom viewer for high-resolution artworks, activated from gallery lightbox** (Confid: stated)
- **Gallery bug fixed: resolved 404 on artworks-taxonomy.json and TypeError in gallery.js from data structure mismatch** (Confid: stated)
- **Hero image optimized: compressed below 1MB maintaining visual quality, part of Wave 8 performance polish** (Confid: stated)
- **MEJORAlo protocol completed: cleaned empty catches, removed console.logs, implemented CSS classes, added focus-visible parity. Verified with browser tests.** (Confid: stated)
- **View in Room feature: lightbox room-mode shows artwork composited on a real Naroa gallery background photo** (Confid: stated)
- **Consultar (purchase intent) button added to lightbox for buyers to contact about artworks** (Confid: stated)
### Error
- **ERROR: Duplicate event listeners on gallery items | CAUSA: addEventListener called on every page load without removeEventListener or guard | FIX: Use { once: true } option or check if listener already attached before adding** (Confid: verified)
- **ERROR: Chromatic aberration breaks in Safari | CAUSA: Safari compositing layer handling differs — mix-blend-mode + filter combination causes rendering artifacts | FIX: Use separate layers for RGB channels with will-change: transform, avoid mixing blend modes with filters on same element** (Confid: verified)
### Ghost
- **GHOST: naroa-web | Última tarea: SEO landing page premium + de-templatize Process/Contact + gallery bug fix | Estado: shipping | Bloqueado: None** (Confid: verified)
