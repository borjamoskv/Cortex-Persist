# CORTEX-Persist: GTM-10 Design Partner Strategy

## 1. El Problema: "Context Fatigue"

La adopción no se logra vendiendo "AI más inteligente". Se logra eliminando la fricción repetitiva.
**Context Fatigue:** El dolor de tener que explicarle al asistente de IA, en cada maldita sesión, cómo funciona tu arquitectura, qué librerías evitas, cuál es tu stack, y tu estilo de código.

**El Insight:** *Developers don’t want smarter AI. They want AI that stops forgetting them.*

---

## 2. El Perfil del "Design Partner" (10 Cupos)

No buscamos a cualquier dev. Buscamos a "Power Users" que están sufriendo los límites de Claude y ChatGPT.

**Criterios de Selección:**
- ⚙️ **Stack:** Python/Rust/TypeScript builders.
- 🏗️ **Arquitectura:** Mantienen proyectos complejos (monorepos, microservicios, código legacy entrelazado).
- ⏱️ **Frecuencia:** Usan herramientas AI (Copilot, Cursor, ChatGPT) diariamente.
- 😡 **Dolor Principal:** Se frustran cuando la IA "alucina" o escribe código genérico rompiendo sus estándares arquitectónicos.

---

## 3. Vectores de "Sniping" (X / Discord / Hacker News)

### Vector A: El Sniping en Hacker News / X (Twitter)
Buscar discusiones sobre "Cursor memory limits", "ChatGPT custom instructions not working", o "AI context window".

**Mensaje (The "Context Fatigue" Hook):**
> "Estoy construyendo una capa de persistencia C5-REAL para asistentes de IA. Básicamente, erradica el 'Context Fatigue'. La IA lee tu código una vez, y **recuerda** tus decisiones arquitectónicas (stack, antipatrones, estilo) para siempre a través de un daemon O(1) local.
> 
> Busco a 10 devs con bases de código complejas para probarlo. ¿Te interesa destrozarlo y decirme por qué no funciona?"

### Vector B: El DM Directo a Power Users (Discord/Telegram)
**Mensaje (The "Show, Don't Tell" Hook):**
> "Hey [Nombre]. He visto tu repo en [Tecnología]. Seguramente estás harto de que Copilot/Claude te escupa código boilerplate genérico que ignora tu arquitectura. 
> 
> Acabo de cerrar la versión *Killer* de **CORTEX-Persist**: Un 'Persistent Dev Companion' que se engancha a tu IDE/Terminal, se aprende tu stack (Memory Genesis), y *nunca más* te vuelve a hacer preguntas redundantes. Tengo 10 cupos para Design Partners. ¿Quieres el binario?"

---

## 4. El "AHA Moment" (T=0 a T=10 mins)

Para que se enganchen irremediablemente (Switching Cost infinito), el proceso de Onboarding debe durar < 2 minutos.

1. **T=0:** El partner ejecuta `python cortex-core/genesis_onboarding.py`.
2. **T=1:** Responde 4 preguntas sobre su stack y antipatrones.
3. **T=2:** El daemon inyecta el `dev_genesis_profile` en el UltraMap local.
4. **T=5:** El partner abre su IDE, pide "Refactoriza este módulo".
5. **T=10 (AHA MOMENT):** La IA devuelve un refactor *usando exactamente las librerías, tipado estricto y convenciones* que el partner definió en el paso 1, sin necesidad de escribir un prompt de 50 líneas.

**Efecto:** La fricción de volver a un asistente "sin estado" (stateless) se vuelve inmanejable. Lock-in instantáneo.
