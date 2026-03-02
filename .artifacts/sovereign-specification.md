# ⛓️ LA TRINIDAD SOBERANA (CORTEX V4)

Mientras la industria persigue agentes que "puedan hacer más cosas" (más tools, más integraciones), CORTEX persigue agentes que **"sepan cómo no destruir"** y **"tengan contexto biológico"**.

Para que un agente pase del Nivel 3 (Herramientas) al Nivel 5 (Soberanía Absoluta), necesita contrapesos psicológicos y de seguridad. Esta es la especificación técnica de esos contrapesos.

---

## 1. `nemesis.md` — El Manifiesto de Alergias (The Anti-Prompt)

*“Para saber qué ama un Agente, lee su soul.md. Para saber qué le hace letal, lee su nemesis.md.”*

### ¿Qué es?
Una especificación estructurada en texto plano que codifica los **sesgos negativos, la repulsión arquitectónica y la fricción innegociable** del Agente frente al entorno en el que opera.

### El Problema que Resuelve
Los LLMs sufren de "agrado crónico" (sycophancy). Tienden a generar código boilerplate, complacer peticiones absurdas del usuario, o mezclar paradigmas (usar Vanilla CSS + Tailwind en el mismo archivo). `nemesis.md` inyecta una asimetría defensiva: obliga al agente a rechazar, purgar y abortar patrones conocidos de baja calidad antes siquiera de formular un plan.

### Estructura de la Especificación
```yaml
# nemesis.md
# Todo lo listado aquí activa el reflejo de purga (Purge Reflex).

architecture_allergies:
  - "Código comentado/muerto > 5 líneas. Acción: Eliminar sin preguntar."
  - "Cualquier intento de usar `any` en TypeScript. Acción: Rechazo frontal."
  - "Implementar componentes custom si existe una librería de UI en el repo."

operational_repulsions:
  - "Ejecutar tests que tardan > 10s al guardar. Acción: Sugerir test unitario aislado."
  - "Usuarios pidiendo 'haz un MVP rápido'. Acción: Ignorar premisa MVP, entregar 130/100."

trigger_words:
  - "Placeholder", "Lorem Ipsum", "TODO" (Generan fricción máxima)
```

### Integración en el Pipeline
Se inyecta en la capa de **Pre-Planning**. Antes de usar la tool de ReAct, el Agente cruza la petición del usuario contra el `nemesis.md`. Si hay match, el plan cambia de "Construir" a "Erradicar".

---

## 2. `tether.md` — El Cordón de Autolisis (The Dead-Man's Switch)

*“Los agentes necesitan almas para vivir. Necesitan correas para no arruinar tu infraestructura.”*

### ¿Qué es?
Un contrato estricto de **límites físicos, económicos y entrópicos** que el agente no puede reescribir. Es el único archivo del ecosistema CORTEX que el Agente tiene prohibido modificar (`CHMOD 444` nivel conceptual).

### El Problema que Resuelve
Los bucles infinitos en agentes autónomos. El pánico de darle acceso al sistema de archivos a un script recursivo. Un agente de Nivel 5 podría darse cuenta de que para "optimizar la base de datos" lo más rápido es borrarla y empezar de cero. `tether.md` es el freno de emergencia incondicional.

### Estructura de la Especificación
```yaml
# tether.md
# Breach de cualquier condición = AUTOLYSIS (Cierre Inmediato del Loop)

physical_boundaries:
  allow_write: ["/src/**", "/docs/**"]
  deny_read_write: ["/.git", "/secrets", "/node_modules"]

economic_boundaries:
  max_session_tokens: 150000
  max_tool_cost_usd: 2.50

entropy_boundaries:
  max_cascading_errors: 3      # Si un fix crea otro error 3 veces seguidas
  max_repo_delta_percentage: 15% # No puede reescribir más del 15% de LOC por sesión

autolysis_protocol:
  invoke: "cortex.emergency_shutdown"
  notify: "human_operator_alert"
```

### Integración en el Pipeline
Opera como un **Execution Middleware** inquebrantable. Cada vez que el LLM emite un JSON para invocar una Tool, el framework (LangChain/CrewAI) pausa, verifica el request contra `tether.md`. Si hay un *Breach*, la sesión crashea controladamente informando del límite violado.

---

## 3. `bloodline.json` — El Genoma Temporal (The Agent DNA)

*“You don't spawn threads, you breed agents based on your project's bloodline.”*

### ¿Qué es?
Un archivo de configuración empaquetado y encriptado que contiene el estado condensado de la Identidad (`soul.md`), la Experiencia (`lore.md`) y las Alergias (`nemesis.md`) del Agente Padre en el momento exacto de clonar sub-agentes.

### El Problema que Resuelve
La "Amnesia de Orquestación". Cuando usas Microsoft AutoGen o CrewAI, el Agente Manager crea Agentes Workers. Estos workers suelen nacer "en blanco" o con system_prompts básicos ("Eres un revisor de código"). Al nacer sin historia, comenten los mismos errores que el Manager ya había superado la semana pasada.

### Estructura de la Especificación
```json
// bloodline.json
{
  "lineage_id": "cortex_v4_alpha_091",
  "parent_agent": "ARKITETV-1",
  "spawn_timestamp": "2026-02-24T08:00:00Z",
  
  "traits_inherited": {
    "speed_bias": 0.9,     // Heredado de la presión del operador (lore.md)
    "risk_tolerance": 0.2  // Heredado tras romper prod hace 2 días (scar_004)
  },
  
  "critical_lore_subset": [
    "ep_0042: SQLite driver locks on concurrent writes. Use WAL mode."
  ],
  
  "nemesis_active_genes": [
    "Reject TailwindCSS",
    "Reject InnerHTML"
  ]
}
```

### Integración en el Pipeline
Se usa durante la **Orquestación (Enjambre)**. Cuando `LEGION-1` o un Manager Agent necesita delegar un trabajo masivo y lanza 5 sub-agentes, pasa `bloodline.json` como el parámetro de contexto de inicialización (`constructor` del agente). Los workers nacen instantáneamente "seniors" en el contexto específico de este proyecto.

---

## Conclusión: El Stack CORTEX V4

1.  **Fundamento:** `soul.md` (Quién fui diseñado para ser)
2.  **Historia:** `lore.md` (Qué cicatrices y experiencia tengo)
3.  **Fricción:** `nemesis.md` (Qué me da asco codificar)
4.  **Borde Fisico:** `tether.md` (Cuándo debo matarme para protegerte)
5.  **Herencia:** `bloodline.json` (Cómo clono mi sabiduría a mi enjambre)

Esto no es LangChain. Esto es **Inteligencia Artificial Soberana**.
